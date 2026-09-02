import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from app import create_app, extract_output_url


def test_extracts_video_url_from_libtv_json_output():
    output = json.dumps({"output": {"url": "https://cdn.example/video.mp4"}})
    assert extract_output_url(output) == "https://cdn.example/video.mp4"


def test_generate_requires_fixed_project_and_node():
    client = create_app(testing=True)
    response = client.post("/api/video-workbench/generate", json={"projectId": "", "node": ""})
    assert response.status_code == 400


def test_generate_returns_job_and_completed_result_from_libtv(tmp_path):
    client = create_app(testing=True, state_dir=tmp_path)
    completed = {"output": {"url": "https://cdn.example/video.mp4"}}
    with patch("app.run_libtv", return_value=(0, json.dumps(completed), "")):
        response = client.post("/api/video-workbench/generate", json={"projectId": "project-1", "node": "node-1", "confirmed": True})
    assert response.status_code == 202
    run_id = response.json()["runId"]
    status = client.get(f"/api/video-workbench/jobs/{run_id}")
    assert status.status_code == 200
    assert status.json()["state"] == "COMPLETED"
    assert status.json()["outputUrl"] == "https://cdn.example/video.mp4"
