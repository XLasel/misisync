"""Bounded HTTP I/O. No source parsing, scheduling, or persistence."""
import httpx
from ..ports import Document


class HttpTransport:
    def __init__(self, settings, *, client=None):
        self.max_bytes = settings.max_download_bytes
        self._owned = client is None
        self.client = client or httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True,
                                                  headers={'User-Agent': 'Misisync/2.0 schedule-reader'})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        if self._owned:
            await self.client.aclose()

    async def request(self, method, url, *, body=None, headers=None):
        async with self.client.stream(method, url, content=body, headers=headers) as response:
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > self.max_bytes:
                    raise ValueError('Response exceeds MAX_DOWNLOAD_BYTES')
            return Document(url=str(response.url), content=bytes(content))
