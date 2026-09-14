from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai_assistant
import master_engine
import vocal_intelligence
import audio_timeline
import audio_intelligence
import songwriting_agent
import songwriter_editor
import song_director
import audio_to_song
import melody_alignment
import production_engine
import project_manager

BASE = Path(__file__).resolve().parent
INPUT_DIR = BASE / "mastering_input"
OUTPUT_DIR = BASE / "optimizer_output"
SEPARATED_DIR = BASE / "separated"
REFERENCE_DIR = BASE / "reference"
PROJECT_DIR = BASE / "project_data"
for d in (INPUT_DIR, OUTPUT_DIR, SEPARATED_DIR, REFERENCE_DIR, PROJECT_DIR):
    d.mkdir(parents=True, exist_ok=True)

APP_VERSION = "11.2.0"
app = FastAPI(title="Eliza Bett Music Lab AI Engineer", version=APP_VERSION)

# Comma-separated production frontend origins can be supplied through CORS_ORIGINS.
# Local development remains enabled by default.
def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in configured.split(",") if origin.strip()] or defaults


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/files/input", StaticFiles(directory=str(INPUT_DIR)), name="input_files")
app.mount("/files/optimizer_output", StaticFiles(directory=str(OUTPUT_DIR)), name="optimizer_files")
app.mount("/files/separated", StaticFiles(directory=str(SEPARATED_DIR)), name="separated_files")


class ChatRequest(BaseModel):
    question: str


class MasterRequest(BaseModel):
    target_lufs: float = -10.5
    ceiling_db: float = -1.0
    intensity: str = "balanced"
    profile: str = "suno6_commercial"


def find_latest_audio() -> Path | None:
    candidates = [p for p in INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def build_analysis() -> dict[str, Any]:
    path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "message": "Аудиофайл пока не загружен."}
    return master_engine.analyze_file(path)


@app.get("/")
def root():
    return {"status": "online", "service": "Eliza Bett Music Lab AI Engineer", "version": APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "version": APP_VERSION}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "track.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}:
        raise HTTPException(400, "Неподдерживаемый формат аудио")
    safe = f"{uuid.uuid4().hex[:8]}_{Path(file.filename or 'track.wav').name}"
    path = INPUT_DIR / safe
    path.write_bytes(await file.read())
    return {"ok": True, "file": safe, "analysis": master_engine.analyze_file(path)}


@app.get("/analysis")
def analysis():
    return build_analysis()


def timeline(source: str = "original"):
    if source == "master":
        masters = [p for p in OUTPUT_DIR.iterdir() if p.is_file() and p.name.endswith("_MASTER.wav")]
        path = max(masters, key=lambda p: p.stat().st_mtime) if masters else None
    elif source == "reference":
        refs = [p for p in REFERENCE_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}]
        path = max(refs, key=lambda p: p.stat().st_mtime) if refs else None
    else:
        path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "source": source}
    return {"status": "ok", "source": source, "file": path.name, **audio_timeline.build_timeline(path)}


@app.get("/timeline")
def get_timeline(source: str = "original"):
    return timeline(source)


@app.get("/songwriter/audio-context")
def songwriter_audio_context():
    path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "message": "Сначала загрузите аудиофайл."}
    return {"status": "ok", "file": path.name, "audio_context": audio_to_song.analyze(path)}


@app.get("/songwriter/melody-map")
def songwriter_melody_map():
    path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "message": "Сначала загрузите аудиофайл."}
    try:
        audio = audio_to_song.analyze(path)
        bpm = (audio.get("tempo") or {}).get("bpm")
        return {"status": "ok", "file": path.name, "melody_map": melody_alignment.analyze(path, bpm=bpm)}
    except Exception as exc:
        raise HTTPException(500, f"Melody map error: {exc}")


@app.get("/intelligence")
def intelligence(source: str = "original"):
    if source == "master":
        masters = [p for p in OUTPUT_DIR.iterdir() if p.is_file() and p.name.endswith("_MASTER.wav")]
        path = max(masters, key=lambda p: p.stat().st_mtime) if masters else None
    elif source == "reference":
        refs = [p for p in REFERENCE_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}]
        path = max(refs, key=lambda p: p.stat().st_mtime) if refs else None
    else:
        path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "source": source}
    return {"status": "ok", "source": source, "file": path.name, **audio_intelligence.analyze_audio(path, segment_sec=5.0)}


class SongwriterRequest(BaseModel):
    request: str
    mode: str = "SONG"
    context: dict[str, Any] = Field(default_factory=dict)
    trend_context: str = ""


class TrendRequest(BaseModel):
    focus: str = ""


class SongMemoryRequest(BaseModel):
    title: str = "Untitled draft"
    text: str
    mode: str = "SONG"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SongNoteRequest(BaseModel):
    note: str


class SongwriterAnalyzeRequest(BaseModel):
    text: str


@app.post("/songwriter/analyze")
def songwriter_analyze(request: SongwriterAnalyzeRequest):
    return {"ok": True, "analysis": songwriter_editor.analyze(request.text)}


@app.post("/songwriter")
def songwriter(request: SongwriterRequest):
    return {"ok": True, "agent": "ELIZA BETT SONGWRITER", "version": songwriting_agent.AGENT_VERSION, "mode": request.mode, "answer": songwriting_agent.generate(request.request, request.mode, request.context, request.trend_context)}


@app.post("/songwriter/trends")
def songwriter_trends(request: TrendRequest):
    return songwriting_agent.trend_report(request.focus)


class SongDirectorRequest(BaseModel):
    request: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    trend_context: str = ""


@app.post("/songwriter/direct")
def songwriter_direct(request: SongDirectorRequest):
    context = dict(request.context or {})
    path = find_latest_audio()
    if path is not None:
        try:
            context["audio_to_song"] = audio_to_song.analyze(path)
            bpm = (context["audio_to_song"].get("tempo") or {}).get("bpm")
            context["melody_map"] = melody_alignment.analyze(path, bpm=bpm)
        except Exception as exc:
            context["audio_to_song_error"] = str(exc)
    return song_director.direct(request.request, context, request.trend_context)


@app.get("/songwriter/memory")
def songwriter_memory_get(limit: int = 12):
    import songwriter_memory
    return {"ok": True, "memory": songwriter_memory.memory(), "dna": songwriter_memory.dna(), "recent": songwriter_memory.recent(limit)}


@app.post("/songwriter/memory")
def songwriter_memory_save(request: SongMemoryRequest):
    import songwriter_memory
    item = songwriter_memory.add_song(request.title, request.text, request.mode, request.tags, request.metadata)
    dna = songwriter_memory.build_local_dna()
    return {"ok": True, "saved": item, "dna": dna}


@app.post("/songwriter/note")
def songwriter_note_save(request: SongNoteRequest):
    import songwriter_memory
    return {"ok": True, "saved": songwriter_memory.add_note(request.note)}


@app.post("/songwriter/dna/rebuild")
def songwriter_dna_rebuild():
    import songwriter_memory
    return {"ok": True, "dna": songwriter_memory.build_local_dna()}


@app.get("/vocal")
def vocal():
    path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "message": "Сначала загрузите аудиофайл."}
    return vocal_intelligence.analyze_vocal(path)


@app.post("/reference")
async def reference(file: UploadFile = File(...)):
    suffix = Path(file.filename or "reference.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}:
        raise HTTPException(400, "Неподдерживаемый формат аудио")
    safe = f"{uuid.uuid4().hex[:8]}_{Path(file.filename or 'reference.wav').name}"
    path = REFERENCE_DIR / safe
    path.write_bytes(await file.read())
    return {"ok": True, "file": safe, "analysis": master_engine.analyze_file(path)}


@app.post("/master")
def master(request: MasterRequest):
    path = find_latest_audio()
    if path is None:
        raise HTTPException(400, "Сначала загрузите аудиофайл")
    reference = None
    refs = [p for p in REFERENCE_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}]
    if refs:
        reference = max(refs, key=lambda p: p.stat().st_mtime)
    return master_engine.run(path, OUTPUT_DIR, request.target_lufs, request.ceiling_db, request.intensity, reference=reference, profile=request.profile)


@app.get("/master/latest")
def latest_master():
    masters = [p for p in OUTPUT_DIR.iterdir() if p.is_file() and p.name.endswith("_MASTER.wav")]
    if not masters:
        raise HTTPException(404, "Мастер ещё не создан")
    path = max(masters, key=lambda p: p.stat().st_mtime)
    return {"file": path.name, "url": f"/files/optimizer_output/{path.name}"}


@app.get("/reference/latest")
def latest_reference():
    refs = [p for p in REFERENCE_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".flac", ".m4a", ".ogg"}]
    if not refs:
        return {"status": "no_reference"}
    path = max(refs, key=lambda p: p.stat().st_mtime)
    return {"file": path.name, "analysis": master_engine.analyze_file(path)}


class ProductionRequest(BaseModel):
    request: str = ""
    profile: str = "suno6_commercial"
    target_lufs: float = -10.5


@app.post("/production/run")
def production_run(request: ProductionRequest):
    result = production_engine.run(INPUT_DIR, OUTPUT_DIR, request.request, request.profile, request.target_lufs)
    if not result.get("ok"):
        raise HTTPException(400, result.get("message", "Production engine error"))
    return result


@app.get("/production/latest")
def production_latest():
    reports = [p for p in OUTPUT_DIR.iterdir() if p.is_file() and "_PRODUCTION_" in p.name and p.suffix == ".json"]
    if not reports:
        return {"status": "no_report"}
    path = max(reports, key=lambda p: p.stat().st_mtime)
    return {"status": "ok", "file": path.name, "url": f"/files/optimizer_output/{path.name}"}


class ProjectRequest(BaseModel):
    name: str = ""
    brief: str = ""
    profile: str = "suno6_commercial"
    lyrics: str = ""
    suno_prompt: str = ""
    notes: str = ""


@app.get("/project")
def project_latest():
    return project_manager.load(PROJECT_DIR)


@app.post("/project/save")
def project_save(request: ProjectRequest):
    return project_manager.save(INPUT_DIR, OUTPUT_DIR, PROJECT_DIR, request.model_dump())


@app.post("/project/export")
def project_export(request: ProjectRequest):
    return project_manager.export_bundle(INPUT_DIR, OUTPUT_DIR, PROJECT_DIR, request.model_dump())


@app.post("/stems")
def stems():
    path = find_latest_audio()
    if path is None:
        raise HTTPException(400, "Сначала загрузите аудиофайл")
    out = SEPARATED_DIR / path.stem
    out.mkdir(parents=True, exist_ok=True)
    device = os.getenv("DEMUCS_DEVICE", "cuda")
    if device not in {"cuda", "cpu"}:
        device = "cuda"
    cmd = [sys.executable, "-m", "demucs", "-d", device, "-n", "htdemucs", "-o", str(SEPARATED_DIR), str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise HTTPException(500, result.stderr or result.stdout or "Demucs error")
    stem_root = SEPARATED_DIR / "htdemucs" / path.stem
    stems = {name: f"/files/separated/{stem_root.relative_to(SEPARATED_DIR).as_posix()}" for name in ("vocals.wav", "drums.wav", "bass.wav", "other.wav") if (stem_root/name).exists()}
    return {"ok": True, "stems": stems}


@app.post("/chat")
def chat(request: ChatRequest):
    context = build_analysis()
    if context.get("status") == "no_audio":
        return {"answer": context["message"], "context": context}
    answer = ai_assistant.answer_local(request.question, context.get("adaptive_analysis", {}), context.get("decisions", []))
    return {"answer": answer, "context": context}
