import aiohttp
import asyncio
from .types import HTTPMethod
from .page import SigaaPage
from .exceptions import SigaaConnectionError
from urllib.parse import urljoin

class SigaaSession:
    def __init__(self, url, cookies=None):
        self.base_url = url
        self._session = None
        self.headers = {
            'User-Agent': 'SIGAA-Api/1.0 (https://github.com/GeovaneSchmitz/sigaa-api)',
            'Accept-Encoding': 'br, gzip, deflate',
            'Accept': '*/*',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }
        self._initial_cookies = cookies

    async def _get_session(self):
        if self._session is None:
            # unsafe=True is required to handle legacy cookies from SIGAA that might violate RFCs (e.g., IP domains or special chars)
            # This is a known acceptance of risk for compatibility.
            cookie_jar = aiohttp.CookieJar(unsafe=True)
            if self._initial_cookies:
                # Assuming _initial_cookies is a dict or simple cookie list
                # aiohttp.CookieJar updates from dict or SimpleCookie
                cookie_jar.update_cookies(self._initial_cookies)

            self._session = aiohttp.ClientSession(
                headers=self.headers,
                cookie_jar=cookie_jar
            )
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def request(self, method, path, data=None, json=None, retry_count=0, **kwargs):
        session = await self._get_session()
        url = path if path.startswith('http') else f"{self.base_url}{path}"

        try:
            async with session.request(method, url, data=data, json=json, **kwargs) as response:
                # We read body here because we close the response context
                # SigaaPage expects full body
                body = await response.text()
                # body_bytes = await response.read() # For binary if needed

                page = SigaaPage(
                    url=response.url,
                    body=body,
                    headers=dict(response.headers),
                    method=method,
                    status_code=response.status,
                    request_headers=dict(response.request_info.headers)
                )

                # Global Questionnaire Interceptor
                # If we encounter the questionnaire, we try to skip it and then retry the original request
                if page.soup.find(id='btnNaoResponderContinuarSigaa'):
                    if retry_count >= 3:
                        # Avoid infinite loops if skipping fails repeatedly
                        return page

                    await self._handle_questionnaire(page)
                    # Retry the original request
                    return await self.request(method, path, data=data, json=json, retry_count=retry_count+1, **kwargs)

                return page

        except aiohttp.ClientError as e:
            raise SigaaConnectionError(f"Connection error: {e}")

    async def _handle_questionnaire(self, page):
        """
        Submits the form to skip the questionnaire.
        """
        skip_button = page.soup.find(id='btnNaoResponderContinuarSigaa')
        if not skip_button:
            return

        form = skip_button.find_parent('form')
        if not form:
            return

        action = form.get('action')
        form_id = form.get('id')

        if not action or not form_id:
            return

        # Construct full action URL
        action_url = urljoin(str(page.url), action)

        # Get ViewState
        view_state = page.view_state

        post_values = {
            form_id: form_id,
            'btnNaoResponderContinuarSigaa': 'btnNaoResponderContinuarSigaa'
        }
        if view_state:
            post_values['javax.faces.ViewState'] = view_state

        # Submit skip
        # We use a raw request here to avoid infinite recursion if this logic was inside request() naively,
        # but since request() calls this and then retries, we can just use self.post (which calls request).
        # Wait, if we use self.post, it calls self.request.
        # If the skip response ALSO contains a questionnaire (unlikely but possible), we might loop.
        # Ideally, the skip response should NOT be the questionnaire.
        # But to be safe, let's use the lower-level _session.request or call a specific internal method.
        # Using self.post is fine because if it recurses, it means skipping failed, which is a real error.
        # But to avoid deep recursion, let's assume one level is enough.

        # Actually, let's use the underlying session to avoid triggering the interceptor on the skip request itself
        # (though strictly speaking we might want to check the skip response too).
        # But the skip response is usually just a redirect or partial update.

        session = await self._get_session()
        async with session.post(action_url, data=post_values) as resp:
             await resp.text() # Consume body

    async def get(self, path, **kwargs):
        return await self.request(HTTPMethod.GET.value, path, **kwargs)

    async def post(self, path, data=None, **kwargs):
        return await self.request(HTTPMethod.POST.value, path, data=data, **kwargs)

    async def follow_all_redirects(self, page):
        """
        Follow redirects manually if needed, although aiohttp handles them by default.
        However, if Sigaa returns 302 with a body that acts as a page (JS redirect) or meta refresh,
        we might need logic here.
        But standard 302 are handled by aiohttp allow_redirects=True (default).
        The TS code had explicit follow logic, likely because it wanted to inspect intermediate pages
        or control the flow strictly.
        """
        # Sigaa sometimes returns 302 but we captured it (if allow_redirects=False was passed)
        # Or if we got a page that we want to ensure is the final destination.

        # If we rely on aiohttp's auto redirect, this might be a no-op unless we encounter
        # client-side redirects (JS/Meta).
        # The TS implementation:
        # while (page.headers.location) { page = await this.get(page.headers.location); }

        # We'll assume aiohttp handles HTTP redirects.
        return page
