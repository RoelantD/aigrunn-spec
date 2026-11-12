"""Credential helpers: Entra ID bearer tokens (preferred) or API keys."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

TokenFn = Callable[[], Awaitable[str]]


class AzureTokenProvider:
    """Caches a DefaultAzureCredential token for one scope and refreshes it before expiry."""

    def __init__(self, scope: str, credential=None):
        self.scope = scope
        self._credential = credential
        self._token: str | None = None
        self._expires_on: float = 0.0

    def _cred(self):
        if self._credential is None:
            from azure.identity.aio import DefaultAzureCredential

            self._credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        return self._credential

    async def __call__(self) -> str:
        if self._token is None or time.time() > self._expires_on - 300:
            tok = await self._cred().get_token(self.scope)
            self._token, self._expires_on = tok.token, float(tok.expires_on)
        return self._token

    async def close(self) -> None:
        if self._credential is not None and hasattr(self._credential, "close"):
            await self._credential.close()
