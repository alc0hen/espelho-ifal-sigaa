from urllib.parse import urljoin
from .exceptions import SigaaInvalidCredentials

class SigaaLogin:
    def __init__(self, session):
        self.session = session
        self.login_status = False

    async def login(self, username, password):
        raise NotImplementedError

class SigaaLoginImpl(SigaaLogin):
    """Generic Sigaa Login implementation (Works for IFSC, IFAL, etc)"""
    def __init__(self, session):
        super().__init__(session)

    async def get_login_form(self):
        page = await self.session.get('/sigaa/verTelaLogin.do')
        return self._parse_login_form(page)

    async def _handle_questionnaire(self, page):
        # Check if questionnaire is present
        skip_button = page.soup.find(id='btnNaoResponderContinuarSigaa')
        if not skip_button:
            return page

        form = skip_button.find_parent('form')
        if not form:
            return page

        action = form.get('action')
        form_id = form.get('id')

        if not action or not form_id:
            return page

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

        # Submit
        # We perform a standard POST to trigger the skip
        new_page = await self.session.post(action_url, data=post_values)
        return new_page

    def _parse_login_form(self, page):
        form = page.soup.find('form', attrs={'name': 'loginForm'})
        if not form:
            raise ValueError('SIGAA: No login form found.')

        action = form.get('action')
        if not action:
            raise ValueError('SIGAA: No action in login form.')

        full_action_url = urljoin(str(page.url), action)

        post_values = {}
        for input_el in form.find_all('input'):
            name = input_el.get('name')
            value = input_el.get('value')
            if name:
                post_values[name] = value if value is not None else ''

        return full_action_url, post_values

    async def login(self, username, password):
        if self.login_status:
            # If already logged in, return current page logic?
            # Ideally we shouldn't be here, but let's assume valid state.
            pass

        action_url, post_values = await self.get_login_form()

        post_values['user.login'] = username
        post_values['user.senha'] = password

        # Submit login
        page = await self.session.post(action_url, data=post_values)

        # Check for questionnaire
        if page.soup.find(id='btnNaoResponderContinuarSigaa'):
            page = await self._handle_questionnaire(page)

        # Check if we are logged in.
        # IFAL might differ slightly in text, but usually "Entrar no Sistema" indicates failure/redirect back to login.
        if 'Entrar no Sistema' in page.body or 'Usuário e/ou senha inválidos' in page.body:
             if 'Usuário e/ou senha inválidos' in page.body:
                 raise SigaaInvalidCredentials('SIGAA: Invalid credentials.')
             else:
                 # Check if it's just a redirect back to login without error message (session expire during login?)
                 # Or maybe successful login redirects elsewhere?
                 # If we see "Entrar no Sistema" again, it failed.
                 raise ValueError('SIGAA: Invalid response after login attempt (Check credentials or system status).')

        self.login_status = True
        return page
