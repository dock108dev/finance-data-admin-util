"""Realtime authentication — API key verification for WS & SSE.

Equivalent to sports-data-admin's realtime/auth.py.
"""

import secrets

from fastapi import HTTPException, Request, WebSocket

from app.config import get_settings


def _check_api_key(api_key: str | None, *, client_label: str) -> bool:
    """Shared validation logic for realtime auth."""
    settings = get_settings()

    if not settings.api_key:
        # Dev mode: allow unauthenticated
        return settings.environment not in {"production", "staging"}

    if not api_key:
        return False

    return secrets.compare_digest(api_key, settings.api_key)


async def verify_ws_api_key(websocket: WebSocket) -> bool:
    """Verify API key for WebSocket connections.

    Checks X-API-Key header or ?api_key query param.
    """
    api_key = (
        websocket.query_params.get("api_key")
        or websocket.headers.get("x-api-key")
    )
    return _check_api_key(api_key, client_label=f"ws-{id(websocket)}")


async def verify_sse_api_key(request: Request) -> None:
    """Verify API key for SSE connections.

    Raises 401 if unauthorized.
    """
    api_key = (
        request.query_params.get("api_key")
        or request.headers.get("x-api-key")
    )
    if not _check_api_key(api_key, client_label=f"sse-{id(request)}"):
        raise HTTPException(status_code=401, detail="Invalid API key")
