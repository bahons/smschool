import os
import sys
import yaml
import json
import uuid
import shutil
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from src.pipeline import process_video

app = FastAPI(
    title="Smart School AI - Safety & Conflict Detection API",
    description="Мектептегі қауіпсіздік пен төбелесті анықтауға арналған REST API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
WEB_DIR = os.path.join(BASE_DIR, "web")
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(WEB_DIR, exist_ok=True)


def get_config():
    cfg_path = os.path.join(BASE_DIR, "config.yaml")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Smart School AI Core", "version": "1.0.0"}


@app.get("/api/demos")
def get_demos():
    """Returns available pre-computed demo results (Calm vs Fight)."""
    demos = []
    for vname, desc in [("video2_calm", "Тыныш сынып (НОРМА)"), ("video1_fight", "Оқушылар төбелесі (ҚАУІП)")]:
        s_path = os.path.join(OUTPUTS_DIR, vname, "summary.json")
        if os.path.exists(s_path):
            with open(s_path, "r", encoding="utf-8") as sf:
                summary = json.load(sf)
            demos.append({
                "id": vname,
                "title": desc,
                "summary": summary,
                "video_url": f"/outputs/{vname}/annotated.mp4",
                "timeline_url": f"/outputs/{vname}/conflict_timeline.png",
                "alert_screenshot_url": f"/outputs/{vname}/alert_screenshot.png" if os.path.exists(os.path.join(OUTPUTS_DIR, vname, "alert_screenshot.png")) else None
            })
    return demos


@app.post("/api/upload")
async def upload_and_process_video(
    file: UploadFile = File(...),
    blur_head: bool = Form(False)
):
    """
    Uploads a video, runs YOLOv8-pose analysis, and returns conflict detection results.
    """
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Тек видео файлдар қабылданады (.mp4, .avi, .mov, .mkv)")

    # Generate unique ID
    task_id = f"upload_{uuid.uuid4().hex[:8]}"
    save_filename = f"{task_id}_{file.filename}"
    saved_path = os.path.join(UPLOADS_DIR, save_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cfg = get_config()
    video_cfg = {
        "path": saved_path,
        "name": task_id,
        "description": f"Жүктелген видео: {file.filename}",
        "expected_alert": False
    }

    try:
        # Run processing pipeline
        result = process_video(video_cfg, cfg, blur_head=blur_head)
        summary = result["summary"]
        v_out_dir = result["video_out_dir"]

        has_alert_screen = os.path.exists(os.path.join(v_out_dir, "alert_screenshot.png"))

        return {
            "status": "success",
            "task_id": task_id,
            "filename": file.filename,
            "summary": summary,
            "video_url": f"/outputs/{task_id}/annotated.mp4",
            "timeline_url": f"/outputs/{task_id}/conflict_timeline.png",
            "alert_screenshot_url": f"/outputs/{task_id}/alert_screenshot.png" if has_alert_screen else None,
            "events_url": f"/outputs/{task_id}/events.json"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Видеоны өңдеу қатесі: {str(e)}")


# Mount outputs directory for media access
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Mount web directory for HTML/CSS/JS frontend
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Smart School API is running. Go to /docs for Swagger UI."}
