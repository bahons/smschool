import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
from scipy.stats import gaussian_kde


class ConflictDetector:
    """
    Computes Conflict Index based on:
    - 9 & 10 keypoints (wrists) kinetic velocity & acceleration
      (Calm desk movements < 320 px/s are filtered out; violent fight wrists reach 1000-8000 px/s)
    - Inter-person distance (proximity)
    - Temporal smoothing
    - 2-second continuous threshold trigger for Alert state
    - KDE spatial density & motion velocity calculation
    """

    def __init__(
        self,
        fps: float = 30.0,
        warning_thresh: float = 0.35,
        danger_thresh: float = 0.55,
        alert_duration_sec: float = 2.0,
        smoothing_alpha: float = 0.20,
        wrist_weight: float = 0.60,
        proximity_weight: float = 0.30,
        motion_weight: float = 0.10
    ):
        self.fps = fps if fps > 0 else 30.0
        self.dt = 1.0 / self.fps
        self.warning_thresh = warning_thresh
        self.danger_thresh = danger_thresh
        self.alert_duration_frames = int(alert_duration_sec * self.fps)
        self.smoothing_alpha = smoothing_alpha

        self.wrist_weight = wrist_weight
        self.proximity_weight = proximity_weight
        self.motion_weight = motion_weight

        # History per track_id: list of keypoints
        self.track_history: Dict[int, deque] = {}
        self.prev_centers: Dict[int, np.ndarray] = {}

        # Alert state tracking
        self.smoothed_index: float = 0.0
        self.consecutive_danger_frames: int = 0
        self.is_alert_triggered: bool = False
        self.first_alert_time: Optional[float] = None
        self.first_alert_frame: Optional[int] = None

        # Events list
        self.events: List[Dict] = []
        self.current_event: Optional[Dict] = None

    def update(
        self,
        tracks: Dict[int, Dict],
        frame_idx: int,
        timestamp: float,
        frame_shape: Tuple[int, int]
    ) -> Dict:
        H, W = frame_shape[:2]
        diag = np.sqrt(H**2 + W**2)

        active_ids = list(tracks.keys())

        # Clean old tracks
        for tid in list(self.track_history.keys()):
            if tid not in tracks:
                del self.track_history[tid]
            if tid in self.prev_centers and tid not in tracks:
                del self.prev_centers[tid]

        wrist_scores = []
        body_velocities = []
        person_centers = []

        for tid, data in tracks.items():
            kpts = np.array(data["keypoints"])
            coords = kpts[:, :2]
            conf = kpts[:, 2] if kpts.shape[1] > 2 else np.ones(len(coords))

            bbox = data.get("bbox", [0, 0, W, H])
            bbox_h = max(30.0, float(bbox[3] - bbox[1]))

            # Center of person
            if conf[11] > 0.3 and conf[12] > 0.3:
                center = (coords[11] + coords[12]) / 2.0
            else:
                center = np.array([(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0])
            person_centers.append(center)

            if tid not in self.track_history:
                self.track_history[tid] = deque(maxlen=6)

            self.track_history[tid].append({"coords": coords, "conf": conf, "bbox_h": bbox_h})

            history = self.track_history[tid]
            if len(history) >= 2:
                prev = history[-2]
                curr = history[-1]

                # Check wrists 9 and 10
                w_speeds = []
                for widx in [9, 10]:
                    if curr["conf"][widx] > 0.30 and prev["conf"][widx] > 0.30:
                        disp_px = np.linalg.norm(curr["coords"][widx] - prev["coords"][widx])
                        speed_px_s = disp_px * self.fps
                        # Calm threshold: ignore below 320 px/s
                        if speed_px_s > 320.0:
                            w_norm = np.clip((speed_px_s - 320.0) / 1400.0, 0.0, 1.0)
                            w_speeds.append(w_norm)

                if len(history) >= 3:
                    prev2 = history[-3]
                    w_accs = []
                    for widx in [9, 10]:
                        if curr["conf"][widx] > 0.30 and prev["conf"][widx] > 0.30 and prev2["conf"][widx] > 0.30:
                            v1 = (prev["coords"][widx] - prev2["coords"][widx]) * self.fps
                            v2 = (curr["coords"][widx] - prev["coords"][widx]) * self.fps
                            acc = np.linalg.norm(v2 - v1) * self.fps
                            if acc > 6000.0:
                                acc_norm = np.clip((acc - 6000.0) / 25000.0, 0.0, 1.0)
                                w_accs.append(acc_norm)

                    if w_accs and w_speeds:
                        wrist_scores.append(0.6 * max(w_accs) + 0.4 * max(w_speeds))
                    elif w_accs:
                        wrist_scores.append(max(w_accs))
                    elif w_speeds:
                        wrist_scores.append(max(w_speeds))
                elif w_speeds:
                    wrist_scores.append(max(w_speeds))

            # Overall body displacement
            if tid in self.prev_centers:
                b_disp = np.linalg.norm(center - self.prev_centers[tid])
                b_speed = b_disp * self.fps
                if b_speed > 120.0:
                    body_velocities.append(np.clip((b_speed - 120.0) / 800.0, 0.0, 1.0))
            self.prev_centers[tid] = center

        # Proximity score (how close are people to each other)
        proximity_score = 0.0
        if len(person_centers) >= 2:
            distances = []
            for i in range(len(person_centers)):
                for j in range(i + 1, len(person_centers)):
                    d = np.linalg.norm(person_centers[i] - person_centers[j])
                    distances.append(d)
            if distances:
                min_dist = min(distances)
                min_dist_norm = min_dist / diag
                if min_dist_norm < 0.22:
                    proximity_score = float(np.clip(1.0 - (min_dist_norm / 0.22), 0.0, 1.0))

        wrist_metric = float(max(wrist_scores)) if wrist_scores else 0.0
        motion_metric = float(np.mean(body_velocities)) if body_velocities else 0.0

        # Combine: Violence requires fast wrist motion
        if wrist_metric < 0.08:
            # Calm hands / sitting at desk -> Conflict is minimal
            raw_index = motion_metric * 0.1
        else:
            # Active hands + proximity
            raw_index = (
                self.wrist_weight * wrist_metric +
                self.proximity_weight * (proximity_score * wrist_metric) +
                self.motion_weight * motion_metric
            )
            # Mutual boost when fighting close-up
            if proximity_score > 0.30 and wrist_metric > 0.20:
                raw_index = min(1.0, raw_index * 1.5)

        raw_index = float(np.clip(raw_index, 0.0, 1.0))

        # Temporal smoothing
        if frame_idx == 0:
            self.smoothed_index = raw_index
        else:
            self.smoothed_index = (
                self.smoothing_alpha * raw_index +
                (1.0 - self.smoothing_alpha) * self.smoothed_index
            )

        # Danger condition: must exceed danger threshold
        if self.smoothed_index >= self.danger_thresh:
            self.consecutive_danger_frames += 1
        else:
            self.consecutive_danger_frames = max(0, self.consecutive_danger_frames - 2)

        # Alert evaluation
        triggered_now = False
        if self.consecutive_danger_frames >= self.alert_duration_frames:
            if not self.is_alert_triggered:
                self.is_alert_triggered = True
                triggered_now = True
                if self.first_alert_time is None:
                    self.first_alert_time = timestamp
                    self.first_alert_frame = frame_idx

            if self.current_event is None:
                self.current_event = {
                    "type": "Conflict",
                    "start_sec": round(timestamp, 2),
                    "end_sec": round(timestamp, 2),
                    "peak_index": round(self.smoothed_index, 3),
                    "confidence": round(self.smoothed_index, 3)
                }
            else:
                self.current_event["end_sec"] = round(timestamp, 2)
                self.current_event["peak_index"] = max(self.current_event["peak_index"], round(self.smoothed_index, 3))
                self.current_event["confidence"] = max(self.current_event["confidence"], round(self.smoothed_index, 3))
        else:
            if self.current_event is not None and self.consecutive_danger_frames == 0:
                self.events.append(self.current_event)
                self.current_event = None

        # Determine state
        if self.consecutive_danger_frames >= self.alert_duration_frames:
            state = "ҚАУІП: ТӨБЕЛЕС"
            state_color = (0, 0, 255)
            state_code = "DANGER"
        elif self.smoothed_index >= self.warning_thresh:
            state = "ЕСКЕРТУ"
            state_color = (0, 215, 255)
            state_code = "WARNING"
        else:
            state = "НОРМА"
            state_color = (0, 255, 0)
            state_code = "NORMAL"

        # KDE / Spatial Density metric
        density_peak = 0.0
        if len(person_centers) >= 3:
            try:
                pts = np.array(person_centers)
                kde = gaussian_kde(pts.T)
                density_peak = float(kde(pts.T).max())
            except Exception:
                density_peak = 0.0

        return {
            "frame_idx": frame_idx,
            "timestamp": timestamp,
            "raw_index": raw_index,
            "conflict_index": self.smoothed_index,
            "state": state,
            "state_code": state_code,
            "state_color": state_color,
            "consecutive_danger_sec": round(self.consecutive_danger_frames / self.fps, 2),
            "is_alert": self.is_alert_triggered,
            "triggered_now": triggered_now,
            "wrist_metric": wrist_metric,
            "proximity_score": proximity_score,
            "motion_metric": motion_metric,
            "density_peak": density_peak,
            "num_persons": len(active_ids)
        }

    def finalize(self):
        if self.current_event is not None:
            self.events.append(self.current_event)
            self.current_event = None
        return self.events
