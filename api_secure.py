from __future__

import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import ai_assistant
import audio_intelligence
import audio_timeline
import audio_to_song
import master_engine
import melody_alignment
import production_engine
import project_manager
import security
import song_director
import songwriter_editor
import songwriting_agent
import telegram_auth
import vocal_intelligence

BASE = Path(__file__).resolve().parent
APP_VERSION = "12.0.0"
ENABLE_DOCS = os.getenv("ENABLE_API_DOCS", "false").lower() == "true"
app = FastAPI(
    title="Eliza Bett Music Lab AI Engineer",
    version=APP_VERSION,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in configured.split(",") if origin.strip()] or defaults


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Telegram-Init-Data"],
)
security.security_middleware(app)

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}


def storage() -> dict[str, Path]:
    return security.user_storage(BASE)


def find_latest_audio() -> Path | None:
    folder = storage()["input"]
    candidates = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def _latest(folder: Path, predicate=None) -> Path | None:
    files = [p for p in folder.rglob("*") if p.is_file()]
    if predicate:
        files = [p for p in files if predicate(p)]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


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


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192)


@app.post("/auth/telegram")
def auth_telegram(request: TelegramAuthRequest):
    try:
        data = telegram_auth.validate_init_data(request.init_data, max_age=int(os.getenv("TELEGRAM_INIT_DATA_MAX_AGE", "3600")))
    except telegram_auth.TelegramAuthError:
        raise HTTPException(401, "Invalid or expired Telegram authentication")
    user = data.get("user") or {}
    return {"ok": True, "authenticated": True, "user": {
        "id": user.get("id"), "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""), "username": user.get("username", ""),
        "language_code": user.get("language_code", ""), "photo_url": user.get("photo_url", ""),
    }, "auth_date": data.get("auth_date"), "start_param": data.get("start_param")}


async def _save_audio(file: UploadFile, folder: Path, default_name: str) -> Path:
    suffix = Path(file.filename or default_name).suffix.lower()
    if suffix not in AUDIO_EXTS:
        raise HTTPException(400, "Неподдерживаемый формат аудио")
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    path = folder / safe_name
    total = 0
    try:
        with path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > security.max_upload_bytes():
                    raise HTTPException(413, "Файл слишком большой")
                out.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    path = await _save_audio(file, storage()["input"], "track.wav")
    try:
        analysis = master_engine.analyze_file(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(400, "Не удалось обработать аудиофайл")
    return {"ok": True, "file": path.name, "analysis": analysis}


@app.get("/analysis")
def analysis():
    return build_analysis()


@app.get("/timeline")
def get_timeline(source: str = "original"):
    dirs = storage()
    if source == "master":
        path = _latest(dirs["output"], lambda p: p.name.endswith("_MASTER.wav"))
    elif source == "reference":
        path = _latest(dirs["reference"], lambda p: p.suffix.lower() in AUDIO_EXTS)
    elif source == "original":
        path = find_latest_audio()
    else:
        raise HTTPException(400, "Invalid source")
    if path is None:
        return {"status": "no_audio", "source": source}
    return {"status": "ok", "source": source, "file": path.name, **audio_timeline.build_timeline(path)}


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
    except Exception:
        raise HTTPException(500, "Melody map generation failed")


@app.get("/intelligence")
def intelligence(source: str = "original"):
    dirs = storage()
    if source == "master":
        path = _latest(dirs["output"], lambda p: p.name.endswith("_MASTER.wav"))
    elif source == "reference":
        path = _latest(dirs["reference"], lambda p: p.suffix.lower() in AUDIO_EXTS)
    elif source == "original":
        path = find_latest_audio()
    else:
        raise HTTPException(400, "Invalid source")
    if path is None:
        return {"status": "no_audio", "source": source}
    try:
        return {"status": "ok", "source": source, "file": path.name, **audio_intelligence.analyze_audio(path, segment_sec=5.0)}
    except Exception:
        raise HTTPException(500, "Audio intelligence analysis failed")


class SongwriterRequest(BaseModel):
    request: str = Field(min_length=1, max_length=12000)
    mode: str = Field(default="SONG", max_length=32)
    context: dict[str, Any] = Field(default_factory=dict)
    trend_context: str = Field(default="", max_length=12000)


class TrendRequest(BaseModel):
    focus: str = Field(default="", max_length=6000)


class SongMemoryRequest(BaseModel):
    title: str = Field(default="Untitled draft", max_length=200)
    text: str = Field(max_length=30000)
    mode: str = Field(default="SONG", max_length=32)
    tags: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SongNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class SongwriterAnalyzeRequest(BaseModel):
    text: str = Field(max_length=30000)


@app.post("/songwriter/analyze")
def songwriter_analyze(request: SongwriterAnalyzeRequest):
    return {"ok": True, "analysis": songwriter_editor.analyze(request.text)}


@app.post("/songwriter")
def songwriter(request: SongwriterRequest):
    try:
        answer = songwriting_agent.generate(request.request, request.mode, request.context, request.trend_context)
    except Exception:
        raise HTTPException(502, "Songwriter service failed")
    return {"ok": True, "agent": "ELIZA BETT SONGWRITER", "version": songwriting_agent.AGENT_VERSION, "mode": request.mode, "answer": answer}


@app.post("/songwriter/trends")
def songwriter_trends(request: TrendRequest):
    try:
        return songwriting_agent.trend_report(request.focus)
    except Exception:
        raise HTTPException(502, "Trend service failed")


class SongDirectorRequest(BaseModel):
    request: str = Field(default="", max_length=12000)
    context: dict[str, Any] = Field(default_factory=dict)
    trend_context: str = Field(default="", max_length=12000)


@app.post("/songwriter/direct")
def songwriter_direct(request: SongDirectorRequest):
    context = dict(request.context or {})
    path = find_latest_audio()
    if path is not None:
        try:
            context["audio_to_song"] = audio_to_song.analyze(path)
            bpm = (context["audio_to_song"].get("tempo") or {}).get("bpm")
            context["melody_map"] = melody_alignment.analyze(path, bpm=bpm)
        except Exception:
            context["audio_to_song_error"] = "analysis_failed"
    try:
        return song_director.direct(request.request, context, request.trend_context)
    except Exception:
        raise HTTPException(502, "Song director service failed")


@app.get("/songwriter/memory")
def songwriter_memory_get(limit: int = 12):
    import songwriter_memory
    limit = max(1, min(limit, 30))
    uid = security.current_user_id()
    return {"ok": True, "memory": songwriter_memory.memory(uid), "dna": songwriter_memory.dna(uid), "recent": songwriter_memory.recent(limit, uid)}


@app.post("/songwriter/memory")
def songwriter_memory_save(request: SongMemoryRequest):
    import songwriter_memory
    uid = security.current_user_id()
    item = songwriter_memory.add_song(request.title, request.text, request.mode, request.tags, request.metadata, uid)
    dna = songwriter_memory.build_local_dna(uid)
    return {"ok": True, "saved": item, "dna": dna}


@app.post("/songwriter/note")
def songwriter_note_save(request: SongNoteRequest):
    import songwriter_memory
    return {"ok": True, "saved": songwriter_memory.add_note(request.note, security.current_user_id())}


@app.post("/songwriter/dna/rebuild")
def songwriter_dna_rebuild():
    import songwriter_memory
    return {"ok": True, "dna": songwriter_memory.build_local_dna(security.current_user_id())}


@app.get("/vocal")
def vocal():
    path = find_latest_audio()
    if path is None:
        return {"status": "no_audio", "message": "Сначала загрузите аудиофайл."}
    try:
        return vocal_intelligence.analyze_vocal(path)
    except Exception:
        raise HTTPException(500, "Vocal analysis failed")


@app.post("/reference")
async def reference(file: UploadFile = File(...)):
    path = await _save_audio(file, storage()["reference"], "reference.wav")
    try:
        analysis = master_engine.analyze_file(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise HTTPException(400, "Не удалось обработать референс")
    return {"ok": True, "file": path.name, "analysis": analysis}


class MasterRequest(BaseModel):
    target_lufs: float = Field(default=-10.5, ge=-24, le=-6)
    ceiling_db: float = Field(default=-1.0, ge=-6, le=-0.1)
    intensity: str = Field(default="balanced", pattern="^(auto|balanced|aggressive|gentle)$")
    profile: str = Field(default="suno6_commercial", max_length=64)


@app.post("/master")
def master(request: MasterRequest):
    dirs = storage()
    path = find_latest_audio()
    if path is None:
        raise HTTPException(400, "Сначала загрузите аудиофайл")
    reference = _latest(dirs["reference"], lambda p: p.suffix.lower() in AUDIO_EXTS)
    try:
        return master_engine.run(path, dirs["output"], request.target_lufs, request.ceiling_db, request.intensity, reference=reference, profile=request.profile)
    except Exception:
        raise HTTPException(500, "Mastering failed")


@app.get("/master/latest")
def latest_master():
    path = _latest(storage()["output"], lambda p: p.name.endswith("_MASTER.wav"))
    if not path:
        raise HTTPException(404, "Мастер ещё не создан")
    return {"file": path.name, "url": f"/files/optimizer_output/{path.name}"}


@app.get("/reference/latest")
def latest_reference():
    path = _latest(storage()["reference"], lambda p: p.suffix.lower() in AUDIO_EXTS)
    if not path:
        return {"status": "no_reference"}
    try:
        return {"file": path.name, "analysis": master_engine.analyze_file(path)}
    except Exception:
        raise HTTPException(500, "Reference analysis failed")


class ProductionRequest(BaseModel):
    request: str = Field(default="", max_length=12000)
    profile: str = Field(default="suno6_commercial", max_length=64)
    target_lufs: float = Field(default=-10.5, ge=-24, le=-6)


@app.post("/production/run")
def production_run(request: ProductionRequest):
    dirs = storage()
    try:
        result = production_engine.run(dirs["input"], dirs["output"], request.request, request.profile, request.target_lufs)
    except Exception:
        raise HTTPException(500, "Production engine failed")
    if not result.get("ok"):
        raise HTTPException(400, "Production request could not be completed")
    return result


@app.get("/production/latest")
def production_latest():
    path = _latest(storage()["output"], lambda p: "_PRODUCTION_" in p.name and p.suffix == ".json")
    if not path:
        return {"status": "no_report"}
    return {"status": "ok", "file": path.name, "url": f"/files/optimizer_output/{path.name}"}


class ProjectRequest(BaseModel):
    name: str = Field(default="", max_length=200)
    brief: str = Field(default="", max_length=10000)
    profile: str = Field(default="suno6_commercial", max_length=64)
    lyrics: str = Field(default="", max_length=30000)
    suno_prompt: str = Field(default="", max_length=12000)
    notes: str = Field(default="", max_length=10000)


@app.get("/project")
def project_latest():
    dirs = storage()
    return project_manager.load(dirs["project"])


@app.post("/project/save")
def project_save(request: ProjectRequest):
    dirs = storage()
    return project_manager.save(dirs["input"], dirs["output"], dirs["project"], request.model_dump())


@app.post("/project/export")
def project_export(request: ProjectRequest):
    dirs = storage()
    try:
        return project_manager.export_bundle(dirs["input"], dirs["output"], dirs["project"], request.model_dump())
    except Exception:
        raise HTTPException(500, "Project export failed")


@app.post("/stems")
def stems():
    dirs = storage()
    path = find_latest_audio()
    if path is None:
        raise HTTPException(400, "Сначала загрузите аудиофайл")
    device = os.getenv("DEMUCS_DEVICE", "cuda")
    if device not in {"cuda", "cpu"}:
        device = "cuda"
    cmd = [sys.executable, "-m", "demucs", "-d", device, "-n", "htdemucs", "-o", str(dirs["separated"]), str(path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, check=False)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Stem separation timed out")
    if result.returncode != 0:
        raise HTTPException(500, "Stem separation failed")
    stem_root = dirs["separated"] / "htdemucs" / path.stem
    stems = {name: f"/files/separated/{stem_root.relative_to(dirs['separated']).as_posix()}" for name in ("vocals.wav", "drums.wav", "bass.wav", "other.wav") if (stem_root/name).exists()}
    return {"ok": True, "stems": stems}


@app.get("/files/{kind}/{relative_path:path}")
def secure_file(kind: str, relative_path: str):
    path = security.resolve_user_file(BASE, kind, relative_path)
    if path is None:
        raise HTTPException(404, "File not found")
    return FileResponse(path)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=6000)


@app.post("/chat")
def chat(request: ChatRequest):
    context = build_analysis()
    if context.get("status") == "no_audio":
        return {"answer": context["message"], "context": context}
    try:
        answer = ai_assistant.answer_local(request.question, context.get("adaptive_analysis", {}), context.get("decisions", []))
    except Exception:
        raise HTTPException(502, "AI assistant failed")
    return {"answer": answer, "context": context}
