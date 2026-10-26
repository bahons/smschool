import cv2
import json
import csv
import time
import os
import sys
import yaml
from typing import Dict, Any, Optional

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from src.stream.video_stream import VideoFileStream
from src.analytics.pose_tracker import PoseTracker
from src.analytics.conflict_detector import ConflictDetector
from src.visualizer.annotator import FrameAnnotator
from src.visualizer.charts import plot_conflict_timeline


def process_video(
    video_cfg: Dict[str, Any],
    global_cfg: Dict[str, Any],
    blur_head: bool = False
) -> Dict[str, Any]:
    """
    Processes a single video:
    - Runs YOLOv8-pose + ByteTrack
    - Computes Conflict Index & Alert state
    - Writes annotated.mp4, conflict_timeline.png, alert_screenshot.png, events.json, events.csv, summary.json
    """
    video_path = video_cfg["path"]
    video_name = video_cfg["name"]
    expected_alert = video_cfg.get("expected_alert", False)

    base_out_dir = global_cfg.get("output", {}).get("base_dir", "outputs")
    video_out_dir = os.path.join(base_out_dir, video_name)
    os.makedirs(video_out_dir, exist_ok=True)

    # Initialize Stream
    stream = VideoFileStream(video_path)
    fps = stream.get_fps()
    width = stream.width
    height = stream.height
    total_frames = stream.total_frames

    print(f"\n[INFO] Басталуда: {video_name} ({video_path}) | FPS: {fps:.1f} | Барлық кадр: {total_frames}")

    # Initialize Modules
    conf_analysis = global_cfg.get("conflict_analysis", {})
    tracker = PoseTracker(
        model_weights=global_cfg.get("model", {}).get("weights", "yolov8n-pose.pt"),
        conf=global_cfg.get("model", {}).get("conf", 0.35),
        iou=global_cfg.get("model", {}).get("iou", 0.5),
        imgsz=global_cfg.get("model", {}).get("imgsz", 640),
        device=global_cfg.get("model", {}).get("device", "cpu")
    )

    detector = ConflictDetector(
        fps=fps,
        warning_thresh=conf_analysis.get("threshold_warning", 0.40),
        danger_thresh=conf_analysis.get("threshold_danger", 0.65),
        alert_duration_sec=conf_analysis.get("alert_duration_seconds", 2.0),
        smoothing_alpha=conf_analysis.get("smoothing_alpha", 0.25),
        wrist_weight=conf_analysis.get("wrist_speed_weight", 0.55),
        proximity_weight=conf_analysis.get("proximity_weight", 0.35),
        motion_weight=conf_analysis.get("motion_weight", 0.10)
    )

    annotator = FrameAnnotator(blur_head=blur_head)

    # Video Writer
    annotated_video_path = os.path.join(video_out_dir, "annotated.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(annotated_video_path, fourcc, fps, (width, height))

    timeline_records = []
    alert_screenshot = None
    alert_screenshot_saved = False
    processing_times = []

    frame_count = 0
    start_total_time = time.time()

    while True:
        t0 = time.time()
        ret, frame, timestamp, current_idx = stream.read()
        if not ret or frame is None:
            break

        # 1. Pose estimation & tracking
        tracks = tracker.track(frame)

        # 2. Conflict Analysis
        metrics = detector.update(tracks, current_idx, timestamp, frame.shape)
        timeline_records.append(metrics)

        # Capture first alert screenshot
        if metrics["triggered_now"] and not alert_screenshot_saved:
            alert_screenshot = frame.copy()
            alert_screenshot_path = os.path.join(video_out_dir, "alert_screenshot.png")
            cv2.imwrite(alert_screenshot_path, alert_screenshot)
            alert_screenshot_saved = True
            print(f"  [ALERT TRIGGERED] Уақыты: {timestamp:.2f}s | Conflict Index: {metrics['conflict_index']:.2f}")

        # Compute instant FPS
        dt_frame = time.time() - t0
        processing_times.append(dt_frame)
        current_fps = 1.0 / dt_frame if dt_frame > 0 else fps

        # 3. Annotation
        annotated_frame = annotator.draw_skeleton(frame, tracks)
        annotated_frame = annotator.draw_hud(annotated_frame, metrics, current_fps)

        writer.write(annotated_frame)
        frame_count += 1

        if frame_count % 30 == 0 or frame_count == total_frames:
            print(f"  Өңделді: {frame_count}/{total_frames} кадр ({timestamp:.1f}s) - Индекс: {metrics['conflict_index']:.2f} [{metrics['state']}]")

    stream.release()
    writer.release()
    total_elapsed = time.time() - start_total_time

    # Finalize events
    events = detector.finalize()

    # 4. Save events.json & events.csv
    events_json_path = os.path.join(video_out_dir, "events.json")
    with open(events_json_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    events_csv_path = os.path.join(video_out_dir, "events.csv")
    with open(events_csv_path, "w", newline="", encoding="utf-8") as f:
        writer_csv = csv.writer(f)
        writer_csv.writerow(["event_type", "start_sec", "end_sec", "peak_index", "confidence"])
        for ev in events:
            writer_csv.writerow([ev["type"], ev["start_sec"], ev["end_sec"], ev["peak_index"], ev["confidence"]])

    # 5. Save conflict_timeline.png
    timeline_png_path = os.path.join(video_out_dir, "conflict_timeline.png")
    plot_conflict_timeline(
        timeline_records=timeline_records,
        danger_thresh=detector.danger_thresh,
        warning_thresh=detector.warning_thresh,
        alert_time=detector.first_alert_time,
        save_path=timeline_png_path,
        title=f"Conflict Index графигі - {video_cfg.get('description', video_name)}"
    )

    # If no alert screenshot but danger occurred, save peak frame
    if not alert_screenshot_saved and len(timeline_records) > 0:
        # Create an informative placeholder or leave it empty if calm
        if detector.is_alert_triggered:
            pass  # Already saved

    # 6. Summary JSON
    avg_latency_ms = (sum(processing_times) / len(processing_times) * 1000) if processing_times else 0.0
    avg_fps = frame_count / total_elapsed if total_elapsed > 0 else 0.0

    summary = {
        "video_name": video_name,
        "video_path": video_path,
        "total_frames": frame_count,
        "duration_seconds": round(frame_count / fps, 2) if fps > 0 else 0.0,
        "fps_video": round(fps, 2),
        "avg_processing_fps": round(avg_fps, 2),
        "avg_latency_ms": round(avg_latency_ms, 2),
        "total_alerts": len(events),
        "alert_triggered": detector.is_alert_triggered,
        "first_alert_time_sec": detector.first_alert_time,
        "expected_alert": expected_alert,
        "test_passed": (detector.is_alert_triggered == expected_alert),
        "peak_conflict_index": round(max([r["conflict_index"] for r in timeline_records], default=0.0), 3)
    }

    summary_json_path = os.path.join(video_out_dir, "summary.json")
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"[DONE] {video_name} өңдеу аяқталды! Сәйкестік: {'ӨТТІ (PASSED)' if summary['test_passed'] else 'ӨТПЕДІ (FAILED)'}\n")
    return {
        "summary": summary,
        "timeline": timeline_records,
        "events": events,
        "video_out_dir": video_out_dir
    }
