import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Optional, Tuple

# COCO Keypoint Skeleton Connections (pair of indices)
SKELETON_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (2, 4),           # Facial/Head
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms / Shoulders
    (5, 11), (6, 12), (11, 12),               # Torso
    (11, 13), (13, 15), (12, 14), (14, 16)   # Legs
]

COLOR_LIMB = (245, 117, 66)    # Cyan/Orange in RGB
COLOR_KPT = (0, 255, 255)      # Yellow
COLOR_WRIST = (255, 0, 128)    # Pink/Magenta highlight for wrists


class FrameAnnotator:
    """
    Visualizes pose skeleton, person IDs, HUD status bar, Conflict Index progress bar,
    timestamp, FPS, and optional head blurring for privacy.
    """

    def __init__(self, blur_head: bool = False):
        self.blur_head = blur_head
        # Attempt to load clean TrueType fonts for Cyrillic support
        self.font_large = self._load_font(26)
        self.font_medium = self._load_font(18)
        self.font_small = self._load_font(14)

    def _load_font(self, size: int):
        font_candidates = [
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\tahoma.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "arial.ttf"
        ]
        for fpath in font_candidates:
            try:
                return ImageFont.truetype(fpath, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def apply_head_blur(self, frame: np.ndarray, keypoints: np.ndarray) -> np.ndarray:
        """
        Blurs head region based on keypoints 0-4 (nose, eyes, ears).
        No face recognition involved.
        """
        H, W = frame.shape[:2]
        head_pts = []
        for i in range(5):
            if keypoints[i, 2] > 0.2:
                head_pts.append(keypoints[i, :2])

        if not head_pts:
            return frame

        head_pts = np.array(head_pts)
        min_x, min_y = np.min(head_pts, axis=0)
        max_x, max_y = np.max(head_pts, axis=0)

        # Add margin around head
        margin_x = max(20, int((max_x - min_x) * 0.8))
        margin_y = max(25, int((max_y - min_y) * 0.9))

        x1 = max(0, int(min_x - margin_x))
        y1 = max(0, int(min_y - margin_y * 1.2))
        x2 = min(W, int(max_x + margin_x))
        y2 = min(H, int(max_y + margin_y * 0.5))

        if x2 > x1 and y2 > y1:
            sub = frame[y1:y2, x1:x2]
            # Heavy Gaussian Blur
            ksize = (max(15, (x2 - x1) // 3 * 2 + 1), max(15, (y2 - y1) // 3 * 2 + 1))
            ksize = (ksize[0] if ksize[0] % 2 != 0 else ksize[0] + 1,
                     ksize[1] if ksize[1] % 2 != 0 else ksize[1] + 1)
            blurred = cv2.GaussianBlur(sub, ksize, 30)
            frame[y1:y2, x1:x2] = blurred

        return frame

    def draw_skeleton(self, frame: np.ndarray, tracks: Dict[int, Dict]) -> np.ndarray:
        """Draws skeletons, wrist emphasis, bounding boxes and track IDs."""
        for tid, data in tracks.items():
            kpts = np.array(data["keypoints"])
            conf = kpts[:, 2] if kpts.shape[1] > 2 else np.ones(len(kpts))
            coords = kpts[:, :2]

            # Privacy head blur
            if self.blur_head:
                frame = self.apply_head_blur(frame, kpts)

            # Draw bones
            for p1_idx, p2_idx in SKELETON_CONNECTIONS:
                if conf[p1_idx] > 0.3 and conf[p2_idx] > 0.3:
                    pt1 = (int(coords[p1_idx][0]), int(coords[p1_idx][1]))
                    pt2 = (int(coords[p2_idx][0]), int(coords[p2_idx][1]))
                    cv2.line(frame, pt1, pt2, (255, 140, 0), 2, cv2.LINE_AA)

            # Draw keypoint dots
            for idx in range(len(coords)):
                if conf[idx] > 0.3:
                    pt = (int(coords[idx][0]), int(coords[idx][1]))
                    # Emphasize wrists (9 and 10)
                    if idx in [9, 10]:
                        cv2.circle(frame, pt, 6, (0, 0, 255), -1, cv2.LINE_AA)
                        cv2.circle(frame, pt, 8, (255, 255, 255), 1, cv2.LINE_AA)
                    else:
                        cv2.circle(frame, pt, 3, (0, 255, 255), -1, cv2.LINE_AA)

            # Draw ID badge
            bbox = data.get("bbox", None)
            if bbox is not None:
                bx1, by1, bx2, by2 = map(int, bbox)
                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (200, 200, 200), 1, cv2.LINE_AA)
                badge_text = f"ID: {tid}"
                (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (bx1, max(0, by1 - 18)), (bx1 + tw + 6, max(18, by1)), (30, 30, 30), -1)
                cv2.putText(frame, badge_text, (bx1 + 3, max(14, by1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return frame

    def draw_hud(
        self,
        frame: np.ndarray,
        metrics: Dict,
        current_fps: float
    ) -> np.ndarray:
        """
        Overlays top status banner, progress bar, timestamp and processing FPS.
        Uses PIL for pristine Cyrillic text rendering.
        """
        H, W = frame.shape[:2]

        # Top Banner background: semi-transparent black overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (W, 70), (20, 20, 25), -1)
        # Bottom info strip
        cv2.rectangle(overlay, (0, H - 32), (W, H), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

        # Convert OpenCV BGR to PIL RGB for clean typography
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        state = metrics.get("state", "НОРМА")
        state_code = metrics.get("state_code", "NORMAL")
        conflict_idx = metrics.get("conflict_index", 0.0)
        timestamp = metrics.get("timestamp", 0.0)

        # Status badge color
        if state_code == "DANGER":
            badge_color = (230, 40, 40)       # Vivid Red
            badge_bg = (90, 10, 10)
        elif state_code == "WARNING":
            badge_color = (255, 190, 0)       # Amber/Yellow
            badge_bg = (80, 60, 10)
        else:
            badge_color = (40, 210, 80)       # Green
            badge_bg = (10, 60, 20)

        # 1. State Badge (Left top)
        badge_box = (15, 12, 280, 58)
        draw.rounded_rectangle(badge_box, radius=8, fill=badge_bg, outline=badge_color, width=2)
        draw.text((25, 20), state, font=self.font_large, fill=(255, 255, 255))

        # 2. Conflict Index Progress Bar (Middle top)
        bar_x = 310
        bar_y = 34
        bar_w = min(320, W - 580)
        bar_h = 16

        # Progress bar container
        draw.text((bar_x, 14), f"Conflict Index: {conflict_idx:.2f}", font=self.font_medium, fill=(230, 230, 230))
        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=4, fill=(50, 50, 55))

        fill_w = int(bar_w * np.clip(conflict_idx, 0.0, 1.0))
        if fill_w > 4:
            draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=4, fill=badge_color)

        # Danger threshold marker
        thresh_x = int(bar_x + bar_w * 0.65)
        draw.line((thresh_x, bar_y - 2, thresh_x, bar_y + bar_h + 2), fill=(255, 255, 255), width=2)

        # 3. Time and FPS info (Right top)
        mins = int(timestamp // 60)
        secs = timestamp % 60
        time_str = f"Уақыт: {mins:02d}:{secs:04.1f}s"
        fps_str = f"FPS: {current_fps:.1f}"

        draw.text((W - 240, 14), time_str, font=self.font_medium, fill=(220, 220, 220))
        draw.text((W - 240, 38), fps_str, font=self.font_medium, fill=(160, 210, 255))

        # 4. Bottom status ribbon
        persons_cnt = metrics.get("num_persons", 0)
        danger_sec = metrics.get("consecutive_danger_sec", 0.0)
        alert_info = f"Адам саны: {persons_cnt}  |  Үздіксіз қауіп: {danger_sec:.1f}s / 2.0s  |  Smart School AI Safety Core"
        draw.text((15, H - 25), alert_info, font=self.font_small, fill=(180, 180, 185))

        # Convert back to BGR for OpenCV
        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return frame
