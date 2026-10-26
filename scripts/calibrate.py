import numpy as np
import yaml
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from src.stream.video_stream import VideoFileStream
from src.analytics.pose_tracker import PoseTracker
from src.analytics.conflict_detector import ConflictDetector


def calibrate():
    """
    Analyzes both calm and fight videos to compute distribution statistics
    (min, mean, 50th, 90th, 95th percentiles, max) to systematically select
    optimal Warning and Danger thresholds.
    """
    config_path = "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    tracker = PoseTracker(
        model_weights=cfg.get("model", {}).get("weights", "yolov8n-pose.pt"),
        conf=cfg.get("model", {}).get("conf", 0.35)
    )

    results = {}

    for key, vcfg in cfg["videos"].items():
        vpath = vcfg["path"]
        vname = vcfg["name"]
        print(f"\n[CALIBRATE] {vname} талдануда ({vpath})...")

        stream = VideoFileStream(vpath)
        detector = ConflictDetector(fps=stream.get_fps())
        indices = []

        while True:
            ret, frame, ts, f_idx = stream.read()
            if not ret or frame is None:
                break
            tracks = tracker.track(frame)
            metrics = detector.update(tracks, f_idx, ts, frame.shape)
            indices.append(metrics["conflict_index"])

        stream.release()

        arr = np.array(indices)
        stats = {
            "min": float(np.min(arr)),
            "mean": float(np.mean(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "max": float(np.max(arr))
        }
        results[key] = stats
        print(f"  {vname} нәтижесі: Мин={stats['min']:.3f}, Орта={stats['mean']:.3f}, 95%={stats['p95']:.3f}, Макс={stats['max']:.3f}")

    # Recommending optimal thresholds:
    # Warning threshold should be above calm video p95
    # Danger threshold should be well separated between calm max and fight peak
    calm_p95 = results.get("normal", {}).get("p95", 0.35)
    calm_max = results.get("normal", {}).get("max", 0.40)
    fight_max = results.get("conflict", {}).get("max", 0.85)

    rec_warning = round(max(0.35, calm_p95 + 0.05), 2)
    rec_danger = round(max(0.60, min(0.70, (calm_max + fight_max) / 2)), 2)

    print(f"\n[ТАЛДАУ ҚОРЫТЫНДЫСЫ]")
    print(f"  Тыныш бейне 95-процентиль: {calm_p95:.2f}, Ең жоғары мән: {calm_max:.2f}")
    print(f"  Конфликт бейне ең жоғары мән: {fight_max:.2f}")
    print(f"  Ұсынылатын ЕСКЕРТУ шегі: {rec_warning}")
    print(f"  Ұсынылатын ҚАУІП шегі:   {rec_danger}")

    # Update config.yaml with calibrated values
    cfg["conflict_analysis"]["threshold_warning"] = rec_warning
    cfg["conflict_analysis"]["threshold_danger"] = rec_danger

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    print(f"[SUCCESS] config.yaml жаңартылды!")


if __name__ == "__main__":
    calibrate()
