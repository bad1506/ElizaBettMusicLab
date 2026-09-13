from __future__ import annotations
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "11.0"
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


def _latest(folder: Path, predicate=None) -> Path | None:
    if not folder.exists():
        return None
    files = [p for p in folder.rglob("*") if p.is_file()]
    if predicate:
        files = [p for p in files if predicate(p)]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def collect(input_dir: str | Path, output_dir: str | Path, project: dict[str, Any] | None = None) -> dict[str, Any]:
    input_dir, output_dir = Path(input_dir), Path(output_dir)
    audio = _latest(input_dir, lambda p: p.suffix.lower() in AUDIO_EXTS)
    master = _latest(output_dir, lambda p: p.name.endswith("_MASTER.wav"))
    report = _latest(output_dir, lambda p: "_PRODUCTION_" in p.name and p.suffix == ".json")
    project = project or {}
    return {
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": project.get("name") or (audio.stem if audio else "Untitled Song"),
        "brief": project.get("brief", ""),
        "profile": project.get("profile", "suno6_commercial"),
        "status": "mastered" if master else ("analyzed" if audio else "empty"),
        "source_audio": audio.name if audio else None,
        "master_audio": master.name if master else None,
        "production_report": report.name if report else None,
        "deliverables": {
            "demo": bool(audio),
            "master": bool(master),
            "production_report": bool(report),
            "lyrics": bool(project.get("lyrics")),
            "suno_prompt": bool(project.get("suno_prompt")),
        },
        "lyrics": project.get("lyrics", ""),
        "suno_prompt": project.get("suno_prompt", ""),
        "notes": project.get("notes", ""),
    }


def save(input_dir: str | Path, output_dir: str | Path, project_dir: str | Path, project: dict[str, Any]) -> dict[str, Any]:
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    data = collect(input_dir, output_dir, project)
    path = project_dir / "project.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "project": data, "file": path.name}


def load(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir) / "project.json"
    if not path.exists():
        return {"ok": True, "status": "empty", "project": collect(Path(project_dir).parent / "mastering_input", Path(project_dir).parent / "optimizer_output")}
    return {"ok": True, "project": json.loads(path.read_text(encoding="utf-8"))}


def export_bundle(input_dir: str | Path, output_dir: str | Path, project_dir: str | Path, project: dict[str, Any]) -> dict[str, Any]:
    project_dir = Path(project_dir)
    result = save(input_dir, output_dir, project_dir, project)
    data = result["project"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in data["name"]).strip("_") or "song"
    bundle = output_dir / f"{safe}_FINAL_PROJECT_{stamp}.zip"
    manifest = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("PROJECT.json", manifest)
        if data.get("source_audio"):
            p = Path(input_dir) / data["source_audio"]
            if p.exists(): z.write(p, f"01_DEMO/{p.name}")
        if data.get("master_audio"):
            p = Path(output_dir) / data["master_audio"]
            if p.exists(): z.write(p, f"02_MASTER/{p.name}")
        if data.get("production_report"):
            p = Path(output_dir) / data["production_report"]
            if p.exists(): z.write(p, f"03_REPORTS/{p.name}")
        z.writestr("04_WRITING/LYRICS.txt", data.get("lyrics", ""))
        z.writestr("04_WRITING/SUNO_PROMPT.txt", data.get("suno_prompt", ""))
        z.writestr("05_NOTES/NOTES.txt", data.get("notes", ""))
    return {"ok": True, "project": data, "bundle": bundle.name, "url": f"/files/optimizer_output/{bundle.name}"}
