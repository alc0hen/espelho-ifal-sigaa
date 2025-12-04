import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .types import HTTPMethod
from .exceptions import SigaaSessionExpired

class SigaaPage:
    def __init__(self, url, body, headers, method, status_code, request_headers=None):
        self.url = url
        self.body = body
        self.headers = headers
        self.method = method
        self.status_code = status_code
        self.request_headers = request_headers or {}
        self._soup = None
        self._view_state = None

        self.check_session_expired()

    @property
    def soup(self):
        if self._soup is None:
            self._soup = BeautifulSoup(self.body, 'lxml')
        return self._soup

    @property
    def view_state(self):
        if self._view_state is None:
            input_el = self.soup.find('input', attrs={'name': 'javax.faces.ViewState'})
            if input_el:
                self._view_state = input_el.get('value')
        return self._view_state

    def check_session_expired(self):
        # Implementation based on TS: statusCode === 302 && location.includes('/sigaa/expirada.jsp')
        if self.status_code == 302:
            location = self.headers.get('location') or self.headers.get('Location')
            if location and '/sigaa/expirada.jsp' in location:
                raise SigaaSessionExpired("SIGAA: Session expired.")

        # Check if the final URL indicates expiration (aiohttp follows redirects by default)
        if '/sigaa/expirada.jsp' in str(self.url):
             raise SigaaSessionExpired("SIGAA: Session expired.")

    def parse_jsfcljs(self, javascript_code):
        """
        Extracts form action and values from JSFCLJS javascript call.
        Replicates logic from SigaaPageIFSC.ts
        """
        if 'getElementById' not in javascript_code:
            raise ValueError('SIGAA: Form not found in JS code.')

        # JSF IDs often contain colons, so we use [^']+ to capture everything until the closing quote
        form_query = re.search(r"document\.getElementById\('([^']+)'\)", javascript_code)
        if not form_query:
            raise ValueError('SIGAA: Form without id in JS code.')

        form_id = form_query.group(1)
        form_el = self.soup.find(id=form_id)
        if not form_el:
            raise ValueError(f'SIGAA: Form with id {form_id} not found in page.')

        form_action = form_el.get('action')
        if not form_action:
            raise ValueError('SIGAA: Form without action.')

        action = urljoin(str(self.url), form_action)
        post_values = {}

        # Get all inputs from the form, except submits
        for input_el in form_el.find_all('input'):
            if input_el.get('type') == 'submit':
                continue
            name = input_el.get('name')
            value = input_el.get('value')
            if name is not None:
                post_values[name] = value

        # Extract the JSON-like object from the JS code
        # The TS regex was: .replace(/if([\S\s]*?),{|},([\S\s]*?)false/gm, '')
        # And then simple replace of quotes.
        # Let's try to mimic or improve parsing.
        # Usually jsfcljs call is: jsfcljs(document.getElementById('...'), {'key':'val'}, '...');

        # We need to extract the second argument which is the object.
        # TS code seems to assume the JS code passed IS the function body or something similar?
        # Re-reading TS: parseJSFCLJS(javaScriptCode: string)
        # It takes the code found in onclick usually.

        # TS Logic:
        # const formPostValuesString = `{${javaScriptCode
        #   .replace(/if([\S\s]*?),{|},([\S\s]*?)false/gm, '')
        #   .replace(/"/gm, '\\"')
        #   .replace(/'/gm, '"')}}`;

        # This TS regex is quite specific. It seems to strip "if(...) ,{" prefix and "}, ... false" suffix.
        # Effectively extracting the content inside the dictionary.

        # Let's look at a sample jsfcljs call (typical JSF):
        # if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('form'),{'j_id_jsp_...':'j_id_jsp_...'},'');}return false

        # The regex seems to remove "if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('form'),{"
        # and "},'');}return false"

        # Let's attempt to use regex to capture the dict content directly.
        # Pattern: ,{ (content) },

        match = re.search(r",\s*\{(.*?)\}\s*,", javascript_code)
        if match:
            json_str = "{" + match.group(1) + "}"

            # Use ast.literal_eval for safer and more robust parsing
            # Replace JS literals with Python equivalents
            py_str = json_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')

            try:
                import ast
                extra_values = ast.literal_eval(py_str)
                if isinstance(extra_values, dict):
                    post_values.update(extra_values)
            except (ValueError, SyntaxError):
                pass

        return {
            'action': action,
            'post_values': post_values
        }
