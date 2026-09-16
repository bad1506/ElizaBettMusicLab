from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable


ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


class OpenAIProvider:
    """Независимый адаптер OpenAI Responses API для SØNA Agent Runtime."""

    name = "openai"

    @staticmethod
    def _model() -> str:
        return os.getenv("OPENAI_MODEL", "gpt-5.6").strip() or "gpt-5.6"

    def generate(self, *, system: str, messages: list[dict[str, Any]]) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/responses"
        payload = {
            "model": self._model(),
            "store": False,
            "tools": [{"type": "web_search"}],
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system}]},
                *messages,
            ],
        }
        return self._extract_text(self._request(endpoint, api_key, payload))

    def generate_with_tools(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        execute_tool: ToolExecutor,
        max_rounds: int = 4,
    ) -> tuple[str, list[dict[str, str]]]:
        """Выполняет Responses API function-calling только через переданный allowlist callback."""
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if not tools:
            return self.generate(system=system, messages=messages), []
        if max_rounds < 1 or max_rounds > 8:
            raise RuntimeError("Invalid tool round limit")

        endpoint = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/responses"
        payload: dict[str, Any] = {
            "model": self._model(),
            "store": False,
            "instructions": system,
            "tools": [{"type": "web_search"}, *tools],
            "input": messages,
        }

        calls: list[dict[str, str]] = []
        response_id: str | None = None

        for _round in range(max_rounds):
            response = self._request(endpoint, api_key, payload)
            response_id = response.get("id")
            output = response.get("output") or []
            function_calls = [item for item in output if item.get("type") == "function_call"]

            if not function_calls:
                text = self._extract_text(response)
                if text:
                    return text, calls
                raise RuntimeError("OpenAI returned an empty response")

            tool_outputs = []
            for call in function_calls:
                name = call.get("name", "")
                call_id = call.get("call_id", "")
                raw_arguments = call.get("arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("arguments must be an object")
                    result = execute_tool(name, arguments)
                    status = "ok"
                    output_text = json.dumps(result, ensure_ascii=False, default=str)
                except Exception as exc:
                    status = "error"
                    output_text = json.dumps(
                        {"ok": False, "error": str(exc)[:500]},
                        ensure_ascii=False,
                    )

                calls.append({"name": name, "status": status})
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": output_text,
                    }
                )

            if not response_id:
                raise RuntimeError("OpenAI response id is missing")
            payload = {
                "model": self._model(),
                "store": False,
                "previous_response_id": response_id,
                "tools": [{"type": "web_search"}, *tools],
                "input": tool_outputs,
            }

        raise RuntimeError("Agent exceeded the maximum tool-call rounds")

    @staticmethod
    def _request(endpoint: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                decoded = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8")[:1000]
            except Exception:
                detail = ""
            raise RuntimeError(f"OpenAI request failed: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("OpenAI request failed: network error") from exc

        data = json.loads(decoded)
        if not isinstance(data, dict):
            raise RuntimeError("OpenAI returned an invalid response")
        return data

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        output_text = response.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        chunks: list[str] = []
        for item in response.get("output") or []:
            if item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                    chunks.append(content["text"])
        return "\n".join(chunks).strip()
