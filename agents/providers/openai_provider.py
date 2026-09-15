from __future__ import annotations

from typing import Any

import ai_assistant


class OpenAIProvider:
    """Адаптер текущего OpenAI-слоя проекта без изменения его API."""

    name = "openai"

    def generate(self, *, system: str, messages: list[dict[str, Any]]) -> str:
        payload = {
            "model": ai_assistant._openai_model(),
            "store": False,
            "tools": [{"type": "web_search"}],
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system}]},
                *messages,
            ],
        }
        return ai_assistant._openai(payload, 120)
