from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "agents" / "skills" / "external" / "SOURCES.json"


def safe_name(value: str) -> str:
    name = re.sub(r"[^a-z0-9_-]", "", value.lower())
    if not name:
        raise SystemExit("Invalid skill name")
    return name[:80]


def main() -> None:
    parser = argparse.ArgumentParser(description="Import one pinned SKILL.md from OpenClaw/Hermes")
    parser.add_argument("source", choices=["openclaw", "hermes"])
    parser.add_argument("path", help="Path to SKILL.md inside the source repository")
    parser.add_argument("--name", default="", help="Local SØNA skill directory name")
    args = parser.parse_args()

    config = json.loads(SOURCES.read_text(encoding="utf-8"))
    commit = config[args.source]["commit"]
    repo = config[args.source]["repository"]
    path = args.path.lstrip("/")
    if not path.endswith("SKILL.md"):
        raise SystemExit("Only SKILL.md files are imported by this adapter")

    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    request = urllib.request.Request(url, headers={"Accept": "text/plain", "User-Agent": "SonaMusicLab/1.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        content = response.read().decode("utf-8")

    name = safe_name(args.name or Path(path).parent.name)
    target = ROOT / "agents" / "skills" / "external" / name / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"Imported {repo}@{commit}:{path} -> {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
