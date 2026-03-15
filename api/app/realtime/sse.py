"""Server-Sent Events endpoint for live market data.

Equivalent to sports-data-admin's realtime/sse.py.
Alternative to WebSocket for clients behind restrictive firewalls.
"""

import asyncio
import json
from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from app.realtime.auth import verify_sse_api_key
from app.realtime.manager import SSEConnection, realtime_manager
from app.realtime.models import is_valid_channel

logger = structlog.get_logger(__name__)

router = APIRouter()

SSE_KEEPALIVE_INTERVAL_S = 15


@router.get("/v1/sse")
async def sse_endpoint(
    request: Request,
    channels: str = Query(..., description="Comma-separated channel list"),
    _auth: None = Depends(verify_sse_api_key),
) -> StreamingResponse:
    """Live market data via Server-Sent Events.

    Query params:
        channels: Comma-separated list (e.g. "prices:CRYPTO,asset:1:price")
        api_key: API key (alternative to X-API-Key header)
    """
    channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()]

    conn = SSEConnection()
    subscribed = []
    rejected = []

    for ch in channel_list:
        if is_valid_channel(ch) and realtime_manager.subscribe(conn, ch):
            subscribed.append(ch)
        else:
            rejected.append(ch)

    logger.info("sse.connected", conn_id=conn.id,
                channels=subscribed, rejected=rejected)

    async def event_stream() -> AsyncGenerator[str, None]:
        # Initial subscription confirmation
        initial = json.dumps({
            "type": "subscribed",
            "channels": subscribed,
            "rejected": rejected,
        })
        yield f"data: {initial}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    data = await asyncio.wait_for(
                        conn.queue.get(),
                        timeout=SSE_KEEPALIVE_INTERVAL_S,
                    )
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive comment to prevent proxy timeouts
                    yield ": keepalive\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            realtime_manager.disconnect(conn)
            logger.info("sse.disconnected", conn_id=conn.id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Bypass nginx buffering
        },
    )
