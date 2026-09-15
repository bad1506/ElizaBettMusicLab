from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .models import SkillSpec


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


class SkillRegistry:
    """Сканирует локальные SØNA skills и совместимые SKILL.md."""

    def __init__(self, root: Path, config_path: Path):
        self.root = root
        self.config_path = config_path
        self._skills: dict[str, SkillSpec] = {}
        self._config: dict[str, Any] = {}
        self.refresh()

    def refresh(self) -> None:
        self._config = json.loads(self.config_path.read_text(encoding="utf-8"))
        self._skills = {}
        if not self.root.is_dir():
            return

        # Поддерживаем как текущий legacy-формат *.md, так и AgentSkills SKILL.md
        # из OpenClaw/Hermes. Более глубокие каталоги позволяют хранить
        # несколько независимых внешних пакетов без конфликтов имён файлов.
        for path in sorted(self.root.rglob("*.md")):
            if path.name != "SKILL.md" and path.parent != self.root and "external" not in path.parts:
                continue
            spec = self._parse(path)
            if spec and spec.name not in self._skills:
                self._skills[spec.name] = spec

    def _parse(self, path: Path) -> SkillSpec | None:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return None

        match = FRONTMATTER_RE.match(raw)
        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                return None
            body = match.group(2).strip()
        else:
            # Старые SØNA *.md не обязаны иметь YAML frontmatter.
            frontmatter = {}
            body = raw.strip()

        name = str(frontmatter.get("name") or path.stem).strip().lower()
        if name == "skill":
            name = path.parent.name.lower()
        description = str(frontmatter.get("description") or self._first_heading(body) or name).strip()
        source = self._source_for(path)
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        return SkillSpec(
            name=name,
            description=description[:1024],
            source=source,
            path=str(path),
            version=str(frontmatter.get("version")) if frontmatter.get("version") else None,
            license=str(frontmatter.get("license")) if frontmatter.get("license") else None,
            metadata=metadata,
            instructions=body[:30000],
        )

    @staticmethod
    def _first_heading(body: str) -> str:
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return ""

    @staticmethod
    def _source_for(path: Path) -> str:
        parts = set(path.parts)
        if "openclaw" in parts:
            return "openclaw"
        if "hermes" in parts:
            return "hermes"
        if "external" in parts:
            return "external"
        return "sona"

    def get(self, name: str | None) -> SkillSpec | None:
        if not name:
            return None
        return self._skills.get(name.strip().lower())

    def all(self) -> list[SkillSpec]:
        return list(self._skills.values())

    def choose(self, message: str, requested: str | None = None) -> SkillSpec | None:
        if requested:
            return self.get(requested)

        text = message.lower()
        routing = self._config.get("routing", {})
        best_name = None
        best_score = 0
        for skill_name, keywords in routing.items():
            if skill_name not in self._skills:
                continue
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > best_score:
                best_name, best_score = skill_name, score
        if best_name:
            return self.get(best_name)

        default_name = self._config.get("agents", {}).get(
            self._config.get("default_agent", "sona-assistant"), {}
        ).get("default_skill", "assistant")
        return self.get(default_name) or self.get("assistant")
