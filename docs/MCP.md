# SØNA MCP integration

SØNA exposes its existing Agent Tool Registry through a standard MCP Streamable HTTP endpoint.

## Endpoint

Production URL:

`https://<SONA_HOST>/mcp`

The endpoint accepts JSON-RPC 2.0 POST requests. It is stateless and returns JSON responses; it does not expose an SSE stream.

## Authentication

`/mcp` is protected by the same security middleware as the private SØNA API.

Use either:

- `Authorization: Bearer <SØNA account session token>`
- `X-Telegram-Init-Data: <validated Telegram init data>`

For production, `ALLOW_LOCAL_UNAUTH` must remain `false`. A request without valid authentication receives HTTP 401 before the MCP handler is executed.

Account session tokens are created by `POST /auth/login` and are valid for the configured session lifetime. Do not place a token in source control or commit it into an MCP client configuration file.

## MCP handshake

1. `initialize`
2. `notifications/initialized`
3. `tools/list`
4. `tools/call`

The server advertises protocol version `2025-06-18` and the `tools` capability.

## Tool boundary

MCP does not implement a second tool system. `tools/list` is generated from `agents/tools/registry.py`, and `tools/call` delegates to the same allowlisted `execute_tool()` used by the SØNA Agent Runtime.

This keeps the architecture:

`MCP client → security middleware → current user context → SØNA tool registry → music services`

The music tools are read-only analysis/advice tools at the current stage. They operate against the authenticated user's workspace through the existing `ContextVar` user context and storage layer.

## Example request

```http
POST /mcp
Authorization: Bearer <SESSION_TOKEN>
Content-Type: application/json
Accept: application/json, text/event-stream

{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
```

Then:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
```

And a tool call:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"music.get_current_analysis","arguments":{}}}
```

## Production checklist

- Set `CORS_ORIGINS` to the real SØNA frontend origin(s).
- Keep `ALLOW_LOCAL_UNAUTH=false`.
- Use HTTPS for the public host.
- Store MCP/account tokens only in the MCP client's secret store.
- Configure the Render service environment and persistent storage before exposing production MCP clients.
- Do not bypass the SØNA API/tool registry with direct external AI credentials.
- Run CI before merging the production branch.

## Current scope

This endpoint exposes SØNA's internal allowlisted tools to MCP-compatible clients. It does not yet turn every SØNA HTTP endpoint into an MCP tool, and it does not expose arbitrary shell, filesystem, payment, or deployment operations.
