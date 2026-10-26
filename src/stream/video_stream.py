from abc import ABC, abstractmethod
import cv2
import os
import time
from typing import Optional, Tuple


class BaseVideoStream(ABC):
    """Abstract Base Class for Video Streams (RTSP or File)."""

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[any], float, int]:
        """
        Reads the next frame.
        Returns:
            (ret, frame, timestamp_sec, frame_idx)
        """
        pass

    @abstractmethod
    def get_fps(self) -> float:
        pass

    @abstractmethod
    def release(self) -> None:
        pass


class VideoFileStream(BaseVideoStream):
    """
    Video file stream matching RTSP stream interface.
    Extracts real FPS from metadata and accurately computes timestamps from frame index.
    """

    def __init__(self, file_path: str, loop: bool = False):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        self.file_path = file_path
        self.loop = loop
        self.cap = cv2.VideoCapture(file_path)

        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video stream for file: {file_path}")

        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS))
        if self.fps <= 0 or self.fps != self.fps:  # Check 0 or NaN
            self.fps = 30.0

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_idx = 0

    def read(self) -> Tuple[bool, Optional[any], float, int]:
        ret, frame = self.cap.read()
        if not ret:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.frame_idx = 0
                ret, frame = self.cap.read()
            else:
                return False, None, self.frame_idx / self.fps, self.frame_idx

        timestamp = self.frame_idx / self.fps
        current_idx = self.frame_idx
        self.frame_idx += 1
        return ret, frame, timestamp, current_idx

    def get_fps(self) -> float:
        return self.fps

    def get_timestamp(self) -> float:
        return self.frame_idx / self.fps

    def release(self) -> None:
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
