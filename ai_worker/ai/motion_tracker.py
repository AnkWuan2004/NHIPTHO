import cv2
import numpy as np


class MotionTracker:

    MAX_FLOW_MAGNITUDE = 12.0

    def __init__(self, blur_kernel=(5, 5)):
        """
        blur_kernel: kich thuoc Gaussian blur truoc khi tinh optical flow.
        - (5, 5): phu hop cho webcam laptop (anh raw it artifact).
        - (7, 7): phu hop cho ESP32-CAM (JPEG artifact nhieu hon, can
          lam mo manh hon de Farneback khong "bam" vao block artifact).
        - KHONG nen tang qua (9,9) vi se lam mo canh, Farneback se kho
          bam duoc chuyen dong tinh te cua long nguc.
        """
        self.blur_kernel = blur_kernel
        self.prev_gray = None
        self.last_flow = None
        self.visual_flow = None
        self.phase_motion = 0.0
        self.phase_direction = -1
        self.signal = []
        self.last_motion_energy = 0.0

    def process(self, roi):

        if roi is None:
            return None

        if roi.size == 0:
            return None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (200, 200))

        gray = cv2.GaussianBlur(gray, self.blur_kernel, 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return None

        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray,
            gray,
            None,
            0.5,
            3,
            21,
            3,
            5,
            1.2,
            0
        )

        self.last_flow = flow

        if not np.all(np.isfinite(flow)):
            self.prev_gray = gray
            return None

        self.last_motion_energy = float(np.median(np.linalg.norm(flow, axis=2)))
        if self.last_motion_energy > self.MAX_FLOW_MAGNITUDE:
            self.prev_gray = gray
            return None

        spatial_flow = cv2.GaussianBlur(flow, (11, 11), 0)
        if self.visual_flow is None:
            self.visual_flow = spatial_flow
        else:
            self.visual_flow = (
                0.82 * self.visual_flow + 0.18 * spatial_flow
            )

        current_phase = float(np.median(self.visual_flow[..., 1]))
        self.phase_motion = 0.85 * self.phase_motion + 0.15 * current_phase

        if self.phase_motion < -0.08:
            self.phase_direction = -1
        elif self.phase_motion > 0.08:
            self.phase_direction = 1

        vertical_motion = flow[..., 1]

        motion_value = float(np.median(vertical_motion))

        self.signal.append(motion_value)
        self.prev_gray = gray

        return motion_value

    @staticmethod
    def phase_color(vertical_motion):
        """Return BGR color for one optical-flow vector.

        OpenCV's positive Y points downward: upward chest movement is treated
        as inhale (red), downward movement as exhale (green).
        """
        return (0, 0, 255) if float(vertical_motion) < 0 else (0, 200, 0)

    def phase_label(self):
        return "HIT VAO" if self.phase_direction < 0 else "THO RA"

    def phase_color_now(self):
        return (0, 0, 255) if self.phase_direction < 0 else (0, 200, 0)

    def draw_particles(
        self,
        frame,
        roi_box,
        grid_step=12,
        min_motion=0.0,
        vector_scale=7.0,
    ):
        """Ve hat/vector optical flow trong ROI.

        Quy uoc cua anh OpenCV: truc Y duong la di xuong.
        - dy < 0: vung nguc di len -> hit vao -> mau do.
        - dy > 0: vung nguc di xuong -> tho ra -> mau xanh.
        """
        if self.visual_flow is None or frame is None or roi_box is None:
            return

        x1, y1, x2, y2 = (int(value) for value in roi_box)
        roi_width = max(1, x2 - x1)
        roi_height = max(1, y2 - y1)
        flow_height, flow_width = self.visual_flow.shape[:2]

        phase_dy = float(np.clip(self.phase_motion * 0.65, -2.0, 2.0))

        for fy in range(grid_step // 2, flow_height, grid_step):
            for fx in range(grid_step // 2, flow_width, grid_step):
                dx, dy = (float(value) for value in self.visual_flow[fy, fx])
                if not np.isfinite(dx + dy):
                    continue

                motion = float(np.hypot(dx, dy))
                if motion < min_motion:
                    continue

                px = x1 + int(fx * roi_width / flow_width)
                py = y1 + int(fy * roi_height / flow_height)
                display_dx = np.clip(dx * 0.35, -1.5, 1.5)
                display_dy = np.clip(0.35 * dy + 0.65 * phase_dy, -2.5, 2.5)
                color = self.phase_color(display_dy)
                end_x = px + int(display_dx * vector_scale)
                end_y = py + int(display_dy * vector_scale)

                cv2.arrowedLine(
                    frame,
                    (px, py),
                    (end_x, end_y),
                    color,
                    1,
                    cv2.LINE_AA,
                    tipLength=0.35,
                )
                cv2.circle(frame, (end_x, end_y), 2, color, -1, cv2.LINE_AA)

    def reset(self):
        self.prev_gray = None
        self.last_flow = None
        self.visual_flow = None
        self.phase_motion = 0.0
        self.phase_direction = -1
        self.last_motion_energy = 0.0
        self.signal.clear()
