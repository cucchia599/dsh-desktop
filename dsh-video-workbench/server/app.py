from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from pydantic import BaseModel


class GenerateRequest(BaseModel):
    projectId: str = ""
    node: str = ""
    confirmed: bool = False
    idempotencyKey: str | None = None


def extract_output_url(raw: str) -> str | None:
    try:
        value: Any = json.loads(raw)
    except json.JSONDecodeError:
        return None

    def walk(item: Any) -> str | None:
        if isinstance(item, dict):
            for key in ("url", "video_url", "videoUrl", "download_url", "downloadUrl"):
                candidate = item.get(key)
                if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
                    return candidate
            for child in item.values():
                found = walk(child)
                if found:
                    return found
        elif isinstance(item, list):
            for child in item:
                found = walk(child)
                if found:
                    return found
        return None

    return walk(value)


def run_libtv(project_id: str, node: str) -> tuple[int, str, str]:
    command = os.getenv("LIBTV_BIN", "/opt/libtv/bin/libtv")
    completed = subprocess.run(
        [command, "node", node, "--project", project_id, "--run"],
        cwd=os.getenv("LIBTV_CWD", "/workspace"),
        capture_output=True,
        text=True,
        timeout=int(os.getenv("LIBTV_TIMEOUT_SECONDS", "7200")),
        check=False,
    )
    return completed.returncode, completed.stdout, completed.stderr


def create_app(testing: bool = False, state_dir: Path | None = None) -> TestClient | FastAPI:
    jobs: dict[str, dict[str, Any]] = {}
    storage = state_dir or Path(os.getenv("VIDEO_WORKBENCH_STATE_DIR", "/data/video-workbench"))
    app = FastAPI(title="DSH Video Workbench Bridge", version="0.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "provider": "libtv-cli"}

    def execute(run_id: str, request: GenerateRequest) -> None:
        job = jobs[run_id]
        job["state"] = "GENERATING"
        code, stdout, stderr = run_libtv(request.projectId, request.node)
        if code == 0:
            job.update({"state": "COMPLETED", "output": stdout.strip(), "outputUrl": extract_output_url(stdout)})
        else:
            job.update({"state": "FAILED", "error": (stderr.strip() or stdout.strip() or f"libtv exited with code {code}")[-4000:]})
        job["updatedAt"] = datetime.now(timezone.utc).isoformat()

    @app.post("/api/video-workbench/generate", status_code=202)
    def generate(request: GenerateRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
        if not request.projectId.strip() or not request.node.strip() or request.confirmed is not True:
            raise HTTPException(status_code=400, detail="projectId, node and confirmed=true are required")
        key = request.idempotencyKey or f"{request.projectId}:{request.node}"
        existing = next((job for job in jobs.values() if job["idempotencyKey"] == key), None)
        if existing:
            return existing
        run_id = f"vw_{uuid.uuid4().hex[:18]}"
        job = {"runId": run_id, "idempotencyKey": key, "provider": "libtv-cli", "state": "QUEUED", "projectId": request.projectId, "node": request.node, "createdAt": datetime.now(timezone.utc).isoformat()}
        jobs[run_id] = job
        background_tasks.add_task(execute, run_id, request)
        return job

    @app.get("/api/video-workbench/jobs/{run_id}")
    def get_job(run_id: str) -> dict[str, Any]:
        job = jobs.get(run_id)
        if not job:
            return {"error": "video job not found"}
        return job

    return TestClient(app) if testing else app


app = create_app()
