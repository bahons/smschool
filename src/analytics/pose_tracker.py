import numpy as np
from typing import Dict, Any, Optional
import os


class PoseTracker:
    """
    YOLOv8-pose based human pose estimator with ByteTrack ID persistence.
    Extracts 17 keypoints and consistent track IDs.
    """

    def __init__(
        self,
        model_weights: str = "yolov8n-pose.pt",
        conf: float = 0.35,
        iou: float = 0.5,
        imgsz: int = 640,
        device: str = "cpu"
    ):
        from ultralytics import YOLO

        self.model = YOLO(model_weights)
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = device

    def track(self, frame: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """
        Runs YOLOv8-pose with tracking on a single frame.

        Returns:
            Dict mapping track_id (int) -> {
                "keypoints": np.ndarray of shape (17, 3) [x, y, conf],
                "bbox": [x1, y1, x2, y2],
                "conf": float
            }
        """
        results = self.model.track(
            source=frame,
            persist=True,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False
        )

        tracks = {}
        if not results or len(results) == 0:
            return tracks

        res = results[0]
        if res.boxes is None or res.keypoints is None:
            return tracks

        boxes = res.boxes.xyxy.cpu().numpy() if res.boxes.xyxy is not None else []
        box_confs = res.boxes.conf.cpu().numpy() if res.boxes.conf is not None else []
        ids = res.boxes.id.cpu().numpy().astype(int) if res.boxes.id is not None else None
        keypoints = res.keypoints.data.cpu().numpy() if res.keypoints.data is not None else []

        for i in range(len(boxes)):
            # If tracking ID is available, use it; otherwise assign frame-local temporary ID
            tid = int(ids[i]) if (ids is not None and i < len(ids)) else (1000 + i)
            kpts = keypoints[i] if i < len(keypoints) else np.zeros((17, 3))
            b_conf = float(box_confs[i]) if i < len(box_confs) else 0.5

            tracks[tid] = {
                "bbox": boxes[i],
                "keypoints": kpts,
                "conf": b_conf
            }

        return tracks
