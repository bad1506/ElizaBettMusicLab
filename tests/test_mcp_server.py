import asyncio
import json

import mcp_server


class _Request:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


def _call(payload):
    return asyncio.run(mcp_server.mcp_http(_Request(payload)))


def test_mcp_initialize():
    response = _call({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["result"]["protocolVersion"] == mcp_server.MCP_PROTOCOL_VERSION
    assert body["result"]["capabilities"]["tools"]["listChanged"] is False


def test_mcp_initialized_notification_returns_202_without_body():
    response = _call({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
    assert response.status_code == 202
    assert response.body == b""


def test_mcp_tools_list_exposes_allowlisted_tools_and_schemas():
    response = _call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert response.status_code == 200
    body = json.loads(response.body)
    tools = {tool["name"]: tool for tool in body["result"]["tools"]}
    assert "music.get_current_analysis" in tools
    assert "music.get_current_intelligence_report" in tools
    assert tools["music.get_current_analysis"]["inputSchema"]["type"] == "object"


def test_mcp_unknown_method_returns_jsonrpc_error():
    response = _call({"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}})
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["error"]["code"] == -32601


def test_mcp_tool_call_uses_existing_registry(monkeypatch):
    monkeypatch.setattr(mcp_server, "execute_tool", lambda name, arguments: {"name": name, "arguments": arguments})
    response = _call(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "music.get_current_analysis", "arguments": {}},
        }
    )
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["result"]["isError"] is False
    assert body["result"]["structuredContent"]["name"] == "music.get_current_analysis"
