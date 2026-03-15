"""API key authentication dependency — equivalent to sports-data-admin's auth middleware."""

from fastapi import Depends, HTTPException, Request

from app.config import Settings, get_settings


async def require_api_key(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate X-API-Key header. Skip for /healthz."""
    if request.url.path == "/healthz":
        return

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
