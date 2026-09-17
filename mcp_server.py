from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from agents.tools import execute_tool, list_tools
from agents.tools.base import ToolError

MCP_PROTOCOL_VERSION = "2025-06-18"
MCP_SERVER_NAME = "sona-music-intelligence"
MCP_SERVER_VERSION = "1.0.0"

router = APIRouter()


def _jsonrpc_result(request_id: Any, result: dict[str, Any]) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


def _jsonrpc_error(request_id: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}},
        status_code=200,
    )


def _tool_catalog() -> list[dict[str, Any]]:
    result = []
    for tool in list_tools():
        result.append(
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["input"],
            }
        )
    return result


@router.post("/mcp")
async def mcp_http(request: Request):
    """Stateless MCP Streamable HTTP endpoint for the SØNA Agent.

    Authentication and per-user storage are provided by the existing security
    middleware. Tool execution is delegated to the existing allowlisted tool
    registry, so MCP cannot bypass SØNA's tool boundary.
    """
    try:
        payload = await request.json()
    except Exception:
        return _jsonrpc_error(None, -32700, "Parse error")

    if not isinstance(payload, dict):
        return _jsonrpc_error(None, -32600, "Invalid Request")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return _jsonrpc_error(request_id, -32600, "Invalid Request")

    if method == "initialize":
        return _jsonrpc_result(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
            },
        )

    if method == "notifications/initialized":
        return JSONResponse(status_code=202, content=None)

    if method == "ping":
        return _jsonrpc_result(request_id, {})

    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": _tool_catalog()})

    if method == "tools/call":
        if not isinstance(params, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _jsonrpc_error(request_id, -32602, "Invalid params")
        try:
            result = execute_tool(name, arguments)
        except ToolError as exc:
            return _jsonrpc_error(request_id, -32602, str(exc))
        return _jsonrpc_result(
            request_id,
            {
                "content": [{"type": "text", "text": _serialize_result(result)}],
                "structuredContent": result,
                "isError": False,
            },
        )

    return _jsonrpc_error(request_id, -32601, f"Method not found: {method}")


def _serialize_result(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
