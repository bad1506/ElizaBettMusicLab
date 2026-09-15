"""Runtime guard for the Music Lab songwriter service.

Python imports sitecustomize automatically at interpreter startup when the project
root is on sys.path. The guard keeps the browser chat transcript from being fed
back to the lyric model as if it were a new songwriting instruction.
"""
from __future__ import annotations

import re

try:
    import songwriting_agent as _songwriting_agent

    _original_generate = getattr(_songwriting_agent, "generate", None)
    if _original_generate is not None and not getattr(_original_generate, "_eliza_guarded", False):

        def _clean_songwriter_request(request, mode="SONG", context=None, trend_context=""):
            text = str(request or "").strip()
            # The frontend sends a compact transcript followed by the actual task.
            # Never let previous AI answers become part of the next user prompt.
            tasks = re.findall(r"(?:^|\\n)Client task:\\s*(.+?)(?=\\n|$)", text, flags=re.IGNORECASE | re.DOTALL)
            if tasks:
                text = tasks[-1].strip()
            else:
                lines = []
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("AI:") or stripped.startswith("Client:"):
                        continue
                    lines.append(line)
                text = "\\n".join(lines).strip()

            # Remove accidental UI/system framing that can leak into the prompt.
            text = re.sub(r"^\\[?(?:VERSE|CHORUS|SONG|HOOK|IDEA)\\]?\\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^Я AI Songwriter\\.?.*?(?=Client task:|$)", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
            return _original_generate(text or "Придумай сильную песню с нуля.", mode, context or {}, trend_context)

        _clean_songwriter_request._eliza_guarded = True
        _songwriting_agent.generate = _clean_songwriter_request
except Exception as exc:
    print(f"Songwriter runtime guard not installed: {exc}")
