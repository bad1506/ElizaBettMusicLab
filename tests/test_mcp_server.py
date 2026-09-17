import json

import pytest

import mcp_server


class _Request:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


@pytest.mark.anyio
async def test_mcp_initialize():
    response = await mcp_server.mcp_http(
        _Request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    )
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["result"]["protocolVersion"] == mcp_server.MCP_PROTOCOL_VERSION
    assert body["result"]["capabilities"]["tools"]["listChanged"] is False


@pytest.mark.anyio
async def test_mcp_tools_list_exposes_allowlisted_tools():
    response = await mcp_server.mcp_http(
        _Request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    )
    assert response.status_code == 200
    body = json.loads(response.body)
    names = {tool["name"] for tool in body["result"]["tools"]}
    assert "music.get_current_analysis" in names
    assert "music.get_current_intelligence_report" in names


@pytest.mark.anyio
async def test_mcp_unknown_method_returns_jsonrpc_error():
    response = await mcp_server.mcp_http(
        _Request({"jsonrpc": "2.0", "id": 3, "method": "unknown/method", "params": {}})
    )
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["error"]["code"] == -32601


@pytest.mark.anyio
async def test_mcp_tool_call_uses_existing_registry(monkeypatch):
    monkeypatch.setattr(mcp_server, "execute_tool", lambda name, arguments: {"name": name, "arguments": arguments})
    response = await mcp_server.mcp_http(
        _Request(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "music.get_current_analysis", "arguments": {}},
            }
        )
    )
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["result"]["isError"] is False
    assert body["result"]["structuredContent"]["name"] == "music.get_current_analysis"
