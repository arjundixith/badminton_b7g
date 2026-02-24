from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qsl, urlencode

from backend.app.main import app as fastapi_app

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]


def _join_paths(left: str, right: str) -> str:
    if not left:
        return right or "/"
    if not right:
        return left
    if left.endswith("/") and right.startswith("/"):
        return left[:-1] + right
    if (not left.endswith("/")) and (not right.startswith("/")):
        return left + "/" + right
    return left + right


def _normalize_api_path(scope: dict[str, Any]) -> dict[str, Any]:
    query_string = scope.get("query_string", b"")
    query_pairs = parse_qsl(
        query_string.decode("utf-8", errors="ignore"),
        keep_blank_values=True,
    )
    forwarded_path: str | None = None
    forwarded_query: list[tuple[str, str]] = []

    for key, value in query_pairs:
        if key == "__path" and forwarded_path is None:
            forwarded_path = "/" + value.lstrip("/")
            continue
        forwarded_query.append((key, value))

    if forwarded_path:
        updated = dict(scope)
        updated["path"] = forwarded_path
        updated["root_path"] = ""
        updated["query_string"] = urlencode(forwarded_query, doseq=True).encode("utf-8")
        return updated

    path = str(scope.get("path", "") or "")
    root_path = str(scope.get("root_path", "") or "")
    raw_path = scope.get("raw_path")

    candidates = [path]
    if root_path:
        candidates.append(_join_paths(root_path, path))
    if isinstance(raw_path, (bytes, bytearray)):
        raw = raw_path.decode("utf-8", errors="ignore").split("?", 1)[0]
        if raw:
            candidates.append(raw)

    for candidate in candidates:
        if candidate == "/api":
            updated = dict(scope)
            updated["path"] = "/"
            updated["root_path"] = ""
            return updated
        if candidate.startswith("/api/"):
            updated = dict(scope)
            updated["path"] = candidate.removeprefix("/api")
            updated["root_path"] = ""
            return updated

    return scope


async def app(scope: dict[str, Any], receive: ASGIReceive, send: ASGISend) -> None:
    if scope.get("type") in {"http", "websocket"}:
        scope = _normalize_api_path(scope)

    await fastapi_app(scope, receive, send)
