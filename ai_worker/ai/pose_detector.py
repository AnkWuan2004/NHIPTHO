from ultralytics import YOLO
import numpy as np


class PoseDetector:

    REQUIRED_KEYPOINTS = (5, 6, 11, 12)
    MIN_KEYPOINT_CONFIDENCE = 0.35

    def __init__(self):
        self.model = YOLO("yolo11n-pose.pt")

    def detect(self, frame):

        results = self.model(frame, verbose=False)

        return results[0]

    @classmethod
    def select_best_person(cls, result):
        """Return the most usable person keypoint set, or ``None``."""
        keypoints = getattr(result, "keypoints", None)
        if keypoints is None or getattr(keypoints, "xy", None) is None:
            return None

        xy = keypoints.xy
        if hasattr(xy, "cpu"):
            xy = xy.cpu().numpy()
        xy = np.asarray(xy, dtype=float)
        if xy.ndim != 3 or xy.shape[1] <= max(cls.REQUIRED_KEYPOINTS):
            return None

        confidence = getattr(keypoints, "conf", None)
        if confidence is not None:
            if hasattr(confidence, "cpu"):
                confidence = confidence.cpu().numpy()
            confidence = np.asarray(confidence, dtype=float)
        else:
            confidence = np.ones(xy.shape[:2], dtype=float)

        candidates = []
        for person_index, person in enumerate(xy):
            points = person[list(cls.REQUIRED_KEYPOINTS)]
            scores = confidence[person_index, list(cls.REQUIRED_KEYPOINTS)]
            if not np.all(np.isfinite(points)) or not np.all(np.isfinite(scores)):
                continue
            if np.any(scores < cls.MIN_KEYPOINT_CONFIDENCE):
                continue

            shoulder_width = float(np.linalg.norm(points[0] - points[1]))
            hip_width = float(np.linalg.norm(points[2] - points[3]))
            torso_height = float(
                np.linalg.norm(np.mean(points[2:4], axis=0) - np.mean(points[0:2], axis=0))
            )
            if shoulder_width < 5 or hip_width < 3 or torso_height < 8:
                continue

            geometry_score = min(1.0, shoulder_width / max(torso_height, 1.0))
            score = float(np.mean(scores)) * (0.7 + 0.3 * geometry_score)
            candidates.append((score, person))

        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
