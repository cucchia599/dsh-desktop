from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from backend.app.core.paths import UPLOADS_DIR, rel_path
from backend.app.media.scene_detect import detect_basic_segments
from backend.app.media.video_probe import probe_video
from backend.app.models.task import Task
from backend.app.video_generation.ingest import build_ingest_record
from backend.app.video_generation.tracking import build_tracking_request, validate_selections


WORKFLOW = "pixel_preserved_background_replacement_v1"
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


def create_task(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("task_id") or f"replica_{uuid.uuid4().hex[:20]}")
    if db.get(Task, task_id):
        return {"status": "blocked", "missing_inputs": ["task_id_unique"], "data": {}}
    task = Task(
        id=task_id,
        task_type="video_replica",
        workflow=WORKFLOW,
        account_id=str(payload.get("account_id") or ""),
        status="draft",
        input_json={
            "generation_mode": "PIXEL_PRESERVED_BACKGROUND_REPLACEMENT",
            "prompt": str(payload.get("prompt") or ""),
            "background_mode": str(payload.get("background_mode") or "UPLOAD"),
            "assets": [],
            "ingest": None,
        },
    )
    db.add(task)
    db.commit()
    return {"status": "ok", "data": _serialize(task)}


async def upload_source(db: Session, task_id: str, upload: UploadFile) -> dict[str, Any]:
    task = db.get(Task, task_id)
    if task is None or task.task_type != "video_replica":
        return {"status": "blocked", "missing_inputs": ["task_id"], "data": {}}
    filename = Path(upload.filename or "source.mp4").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return {"status": "blocked", "missing_inputs": ["supported_video_format"], "data": {}}
    target_dir = (UPLOADS_DIR / "video-replica" / task_id).resolve()
    if not target_dir.is_relative_to(UPLOADS_DIR.resolve()):
        return {"status": "blocked", "missing_inputs": ["storage_path"], "data": {}}
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"source{extension}"
    with target.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            handle.write(chunk)
    probe = probe_video(target)
    segments = detect_basic_segments(float(probe.get("duration") or 0))
    try:
        ingest = build_ingest_record(
            task_id=task_id,
            source_path=target,
            probe=probe,
            segments=segments,
        )
    except ValueError as exc:
        target.unlink(missing_ok=True)
        return {"status": "blocked", "missing_inputs": ["valid_video"], "warnings": [str(exc)], "data": {}}
    task.status = "awaiting_selection"
    task.input_json = {**(task.input_json or {}), "assets": [{"role": "SOURCE_VIDEO", "path": rel_path(target)}], "ingest": ingest}
    db.commit()
    return {"status": "ok", "data": _serialize(task)}


def get_task(db: Session, task_id: str) -> dict[str, Any]:
    task = db.get(Task, task_id)
    if task is None or task.task_type != "video_replica":
        return {"status": "blocked", "missing_inputs": ["task_id"], "data": {}}
    return {"status": "ok", "data": _serialize(task)}


def save_selections(db: Session, task_id: str, selections: list[dict[str, Any]]) -> dict[str, Any]:
    task = db.get(Task, task_id)
    if task is None or task.task_type != "video_replica":
        return {"status": "blocked", "missing_inputs": ["task_id"], "data": {}}
    missing = validate_selections(selections)
    if missing:
        return {"status": "blocked", "missing_inputs": missing, "data": {}}
    task.input_json = {**(task.input_json or {}), "selections": selections}
    task.status = "ready"
    db.commit()
    return {"status": "ok", "data": _serialize(task)}


def prepare_tracking(db: Session, task_id: str) -> dict[str, Any]:
    task = db.get(Task, task_id)
    if task is None or task.task_type != "video_replica":
        return {"status": "blocked", "missing_inputs": ["task_id"], "data": {}}
    try:
        request = build_tracking_request(task_id, list((task.input_json or {}).get("selections") or []))
    except (RuntimeError, ValueError) as exc:
        return {"status": "blocked", "missing_inputs": ["sam2", "cutie"], "warnings": [str(exc)], "data": {}}
    task.input_json = {**(task.input_json or {}), "tracking_request": request}
    task.status = "queued"
    db.commit()
    return {"status": "ok", "data": _serialize(task)}


def _serialize(task: Task) -> dict[str, Any]:
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "workflow": task.workflow,
        "status": task.status,
        "input": task.input_json or {},
        "preservation_policy": {
            "foreground_pixels": True,
            "motion": True,
            "original_audio": True,
            "video_regeneration": False,
            "lip_sync": False,
            "tts": False,
        },
    }
