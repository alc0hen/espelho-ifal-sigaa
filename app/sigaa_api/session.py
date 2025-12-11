import aiohttp
import asyncio
from .types import HTTPMethod
from .page import SigaaPage
from .exceptions import SigaaConnectionError

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

    async def request(self, method, path, data=None, json=None, **kwargs):
        session = await self._get_session()
        url = path if path.startswith('http') else f"{self.base_url}{path}"

        try:
            async with session.request(method, url, data=data, json=json, **kwargs) as response:
                # We read body here because we close the response context
                # SigaaPage expects full body
                body = await response.text()
                # body_bytes = await response.read() # For binary if needed

                return SigaaPage(
                    url=response.url,
                    body=body,
                    headers=dict(response.headers),
                    method=method,
                    status_code=response.status,
                    request_headers=dict(response.request_info.headers)
                )
        except aiohttp.ClientError as e:
            raise SigaaConnectionError(f"Connection error: {e}")

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
