"""Realtime data layer — WebSocket, SSE, and DB polling for live market data.

Equivalent to sports-data-admin's realtime/ module.

Channel format:
    prices:{asset_class}          — Live price updates for asset class
    asset:{asset_id}:price        — Single asset price stream
    asset:{asset_id}:signals      — Signal alerts for an asset
    signals:alpha                 — All alpha signal updates
"""
