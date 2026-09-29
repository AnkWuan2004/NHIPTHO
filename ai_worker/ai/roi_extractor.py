import cv2
import numpy as np


class ROIExtractor:

    MIN_WIDTH_PX = 30
    MIN_HEIGHT_PX = 30
    MIN_AREA_RATIO = 0.005
    MAX_AREA_RATIO = 0.60

    def get_chest_roi(
            self,
            frame,
            left_shoulder,
            right_shoulder,
            left_hip,
            right_hip
    ):
        points = np.asarray(
            [left_shoulder, right_shoulder, left_hip, right_hip],
            dtype=float,
        )
        if points.shape != (4, 2) or not np.all(np.isfinite(points)):
            return None

        shoulder_width = float(np.linalg.norm(points[0] - points[1]))
        torso_height = float(
            np.linalg.norm(np.mean(points[2:4], axis=0) - np.mean(points[0:2], axis=0))
        )
        if shoulder_width < self.MIN_WIDTH_PX or torso_height < self.MIN_HEIGHT_PX:
            return None

        x1 = int(min(left_shoulder[0], right_shoulder[0]))
        x2 = int(max(left_shoulder[0], right_shoulder[0]))

        shoulder_y = (
            left_shoulder[1] +
            right_shoulder[1]
        ) / 2

        hip_y = (
            left_hip[1] +
            right_hip[1]
        ) / 2

        horizontal_padding = max(8.0, shoulder_width * 0.18)
        y1 = int(shoulder_y - torso_height * 0.10)

        y2 = int(
            shoulder_y + torso_height * 0.48
        )

        x1 = int(x1 - horizontal_padding)
        x2 = int(x2 + horizontal_padding)

        return x1, y1, x2, y2

    @classmethod
    def validate_roi(cls, frame_shape, roi):
        if roi is None or len(roi) != 4 or len(frame_shape) < 2:
            return False
        height, width = frame_shape[:2]
        x1, y1, x2, y2 = (int(value) for value in roi)
        roi_width = x2 - x1
        roi_height = y2 - y1
        if roi_width < cls.MIN_WIDTH_PX or roi_height < cls.MIN_HEIGHT_PX:
            return False
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            return False
        area_ratio = (roi_width * roi_height) / float(width * height)
        return cls.MIN_AREA_RATIO <= area_ratio <= cls.MAX_AREA_RATIO
