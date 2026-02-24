from collections.abc import Awaitable, Callable
from typing import Any

from backend.app.main import app as fastapi_app

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


async def app(scope: dict[str, Any], receive: ASGIReceive, send: ASGISend) -> None:
    if scope.get("type") in {"http", "websocket"}:
        path = scope.get("path", "")
        if path == "/api":
            scope = dict(scope)
            scope["path"] = "/"
        elif path.startswith("/api/"):
            scope = dict(scope)
            scope["path"] = path.removeprefix("/api")

    await fastapi_app(scope, receive, send)

