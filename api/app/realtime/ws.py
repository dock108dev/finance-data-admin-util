"""WebSocket endpoint for live market data streaming.

Equivalent to sports-data-admin's realtime/ws.py.

Protocol:
  Client → Server:
    {"type": "subscribe", "channels": ["prices:CRYPTO", "asset:1:price"]}
    {"type": "unsubscribe", "channels": ["prices:CRYPTO"]}
    {"type": "pong"}

  Server → Client:
    {"type": "subscribed", "channels": [...], "rejected": [...]}
    {"type": "unsubscribed", "channels": [...]}
    {"type": "price_update", "channel": "...", "seq": 1, ...}
    {"type": "ping"}
"""

import asyncio
import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.auth import verify_ws_api_key
from app.realtime.manager import WSConnection, realtime_manager
from app.realtime.models import is_valid_channel

logger = structlog.get_logger(__name__)

router = APIRouter()

WS_PING_INTERVAL_S = 25
MAX_MESSAGE_SIZE = 256 * 1024  # 256 KB


@router.websocket("/v1/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Live market data WebSocket endpoint."""

    # Auth before accept
    if not await verify_ws_api_key(websocket):
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    conn = WSConnection(websocket)
    logger.info("ws.connected", conn_id=conn.id)

    # Start ping loop
    ping_task = asyncio.create_task(_ping_loop(websocket, conn.id))

    try:
        while True:
            raw = await websocket.receive_text()

            if len(raw) > MAX_MESSAGE_SIZE:
                await websocket.send_json({
                    "type": "error",
                    "message": "Message too large",
                })
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = msg.get("type")

            if msg_type == "subscribe":
                channels = msg.get("channels", [])
                subscribed = []
                rejected = []

                for ch in channels:
                    if not is_valid_channel(ch):
                        rejected.append(ch)
                    elif realtime_manager.subscribe(conn, ch):
                        subscribed.append(ch)
                    else:
                        rejected.append(ch)

                await websocket.send_json({
                    "type": "subscribed",
                    "channels": subscribed,
                    "rejected": rejected,
                })
                logger.info("ws.subscribed", conn_id=conn.id,
                            channels=subscribed, rejected=rejected)

            elif msg_type == "unsubscribe":
                channels = msg.get("channels", [])
                for ch in channels:
                    realtime_manager.unsubscribe(conn, ch)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "channels": channels,
                })

            elif msg_type == "pong":
                pass  # Keepalive acknowledged

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        logger.info("ws.disconnected", conn_id=conn.id)
    except Exception as e:
        logger.error("ws.error", conn_id=conn.id, error=str(e))
    finally:
        ping_task.cancel()
        realtime_manager.disconnect(conn)


async def _ping_loop(websocket: WebSocket, conn_id: str) -> None:
    """Send periodic ping frames to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(WS_PING_INTERVAL_S)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except asyncio.CancelledError:
        pass
