"""
breathing_worker.py
-------------------
Worker do nhip tho tu camera laptop/USB (mac dinh) hoac ESP32-CAM.

Vi du:
    python breathing_worker.py                 # camera laptop so 0
    python breathing_worker.py --camera 1      # camera so 1
    python breathing_worker.py --espcam http://192.168.1.50/stream
"""

import argparse
import time

import cv2
import matplotlib.pyplot as plt
import numpy as np
import requests
from ultralytics import YOLO
import os
from datetime import datetime, timezone
from ai.roi_extractor import ROIExtractor
from ai.pose_detector import PoseDetector
from ai.motion_tracker import MotionTracker
from ai.signal_filter import SignalFilter
from ai.breathing_rate import BreathingRateEstimator
from ai.anomaly_detector import AnomalyDetector


ESPCAM_URL = "http://172.20.10.4/stream"

CAPTURE_DIR = "captures"
WORKER_TOKEN = os.getenv("BREATHING_WORKER_TOKEN", "local-worker-token")
MIN_ACCEPTABLE_FPS = 5.0
os.makedirs(CAPTURE_DIR, exist_ok=True)
def parse_args():
    parser = argparse.ArgumentParser(
        description="Breathing rate worker (laptop camera or ESP32-CAM) -> push to API"
    )
    parser.add_argument(
        "--api", default="http://127.0.0.1:5000",
        help="Base URL cua Flask backend (mac dinh http://127.0.0.1:5000)"
    )
    parser.add_argument(
        "--camera", type=int, default=0,
        help="Chi so camera laptop/USB (mac dinh 0). Bo qua neu dung --espcam."
    )
    parser.add_argument(
        "--espcam", type=str, default=None,
        help=(
            "URL MJPEG stream cua ESP32-CAM. Neu truyen tham so nay, "
            "worker se dung ESP32-CAM thay cho camera laptop."
        )
    )
    parser.add_argument(
        "--interval", type=float, default=60.0,
        help="Do dai MOI khoi tin hieu KHONG chong lap, don vi giay (mac dinh 60)"
    )
    parser.add_argument(
        "--roi-update-every", type=int, default=10,
        help="So frame giua 2 lan chay lai YOLO de cap nhat vi tri ROI (mac dinh 10)"
    )
    parser.add_argument(
        "--roi-smoothing", type=float, default=0.3,
        help="He so lam muot EMA khi ROI di chuyen, 0-1 (mac dinh 0.3)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Chay khong mo cua so OpenCV/Matplotlib, phu hop may chu hoac smoke test."
    )
    args = parser.parse_args()

    if args.espcam:
        args.espcam = args.espcam.strip()
    if args.espcam and not (
        args.espcam.startswith("http://") or args.espcam.startswith("https://")
    ):
        parser.error(
            f"URL ESP32-CAM khong hop le: {args.espcam!r}\n"
            "Truyen --espcam http://IP/stream"
        )

    return args


def open_capture(args):
    is_espcam = bool(args.espcam)
    source = args.espcam if is_espcam else args.camera
    label = f"ESP32-CAM: {source}" if is_espcam else f"camera laptop so {source}"
    print(f"[worker] Dang mo {label}")
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    if not cap.isOpened():
        raise RuntimeError(
            f"Khong mo duoc {label}.\n"
            "Neu dung camera laptop, kiem tra camera dang duoc he thong cap quyen "
            "va thu --camera 1. Neu dung ESP32-CAM, kiem tra IP/stream."
        )
    print(f"[worker] Da mo {label}")
    return cap, is_espcam


def reopen_espcam(url, max_retries=10, wait_sec=3.0):
    """Thu mo lai stream ESP32-CAM sau khi mat ket noi."""
    for attempt in range(1, max_retries + 1):
        print(f"[worker] Thu ket noi lai ESP32-CAM lan {attempt}/{max_retries}...")
        time.sleep(wait_sec)
        cap = cv2.VideoCapture(url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print("[worker] Da ket noi lai ESP32-CAM thanh cong")
                return cap
        cap.release()
    raise RuntimeError(
        f"Khong the ket noi lai ESP32-CAM sau {max_retries} lan thu. "
        "Kiem tra nguon dien va WiFi cua ESP32-CAM."
    )


def smooth_roi(old_roi, new_roi, alpha):
    if old_roi is None:
        return new_roi
    return tuple(int(old_roi[i] + alpha * (new_roi[i] - old_roi[i])) for i in range(4))


def detect_chest_roi(model, roi_extractor, frame):
    result = model(frame, verbose=False)[0]
    person = PoseDetector.select_best_person(result)
    if person is None:
        return None, result, "chua thay nguoi co du diem vai/hong"
    ls, rs, lh, rh = person[5], person[6], person[11], person[12]
    roi = roi_extractor.get_chest_roi(frame, ls, rs, lh, rh)
    if roi is None:
        return None, result, "pose co nhung ROI nguc qua nho/khong hop le"
    x1, y1, x2, y2 = roi
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    if roi_extractor.validate_roi(frame.shape, (x1, y1, x2, y2)):
        return (x1, y1, x2, y2), result, "da khoa ROI nguc"
    return None, result, "ROI nguc vuot bien anh"


def assess_block_quality(block_signal, min_fps=MIN_ACCEPTABLE_FPS, max_amplitude=8.0):
    """Validate a raw optical-flow block before filtering/counting peaks."""
    if not block_signal or len(block_signal) < 10:
        return {"valid": False, "reason": f"insufficient_samples={len(block_signal or [])}"}

    timestamps = np.asarray([item[0] for item in block_signal], dtype=float)
    values = np.asarray([item[1] for item in block_signal], dtype=float)
    if timestamps.size != values.size or not np.all(np.isfinite(timestamps)) or not np.all(np.isfinite(values)):
        return {"valid": False, "reason": "non_finite_signal_or_timestamp"}
    if np.any(np.diff(timestamps) <= 0):
        return {"valid": False, "reason": "timestamps_not_monotonic"}

    duration = float(timestamps[-1] - timestamps[0])
    if duration <= 0:
        return {"valid": False, "reason": "non_positive_duration"}
    fps = float((len(values) - 1) / duration)
    if fps < min_fps:
        return {"valid": False, "reason": f"low_fps={fps:.2f}<{min_fps:.2f}", "fps": fps}

    amplitude = float(np.ptp(values))
    if amplitude > max_amplitude:
        return {"valid": False, "reason": f"excessive_motion_amplitude={amplitude:.3f}", "fps": fps}

    return {
        "valid": True,
        "reason": "ok",
        "fps": fps,
        "duration": duration,
        "values": values,
        "timestamps": timestamps,
        "amplitude": amplitude,
    }


def summarize_signal_quality(filtered_signal, peaks, fps):
    signal = np.atleast_1d(np.asarray(filtered_signal, dtype=float))
    amplitude = float(np.ptp(signal)) if signal.size else None
    regularity = 0.0
    if fps and len(peaks) >= 3:
        intervals = np.diff(np.asarray(peaks, dtype=float)) / fps
        mean_interval = float(np.mean(intervals))
        if mean_interval > 0:
            regularity = float(np.clip(1.0 - (np.std(intervals) / mean_interval), 0.0, 1.0))
    elif len(peaks) == 2:
        regularity = 0.5

    fps_score = float(np.clip((fps or 0.0) / 15.0, 0.0, 1.0))
    amplitude_score = 1.0 if amplitude is not None and amplitude > 1e-6 else 0.0
    quality_score = float(np.clip(0.45 * fps_score + 0.35 * amplitude_score + 0.20 * regularity, 0.0, 1.0))
    quality = "valid" if (fps or 0.0) >= MIN_ACCEPTABLE_FPS and len(peaks) >= 2 and amplitude_score else "uncertain"
    reason = f"fps={fps:.2f}; peaks={len(peaks)}; amplitude={amplitude:.6f}" if fps else "missing_fps"
    return quality, quality_score, reason, amplitude, regularity


def push_bpm(
    api_base,
    bpm_value,
    frame,
    source,
    quality,
    quality_score,
    quality_reason,
    features,
    anomaly="unknown",
    anomaly_score=None,
    anomaly_reason=None,
):
    if not np.isfinite(bpm_value) or bpm_value <= 0:
        print(f"[worker] Bo qua block khong hop le, khong ghi BPM={bpm_value!r}")
        return

    url = f"{api_base}/api/measurements"

    image_path = None

    if bpm_value > 25 or bpm_value < 5:
        filename = datetime.now().strftime("%Y%m%d_%H%M%S.jpg")
        image_path = os.path.join(CAPTURE_DIR, filename)
        cv2.imwrite(image_path, frame)

    detect_time = datetime.now()

    print("=" * 60)
    print(f"[Worker] Phát hiện cảnh báo : {detect_time:%Y-%m-%d %H:%M:%S}")
    print(f"[Worker] BPM              : {bpm_value:.2f}")
    print(f"[Worker] Ảnh              : {image_path}")
    print("=" * 60)

    payload = {
        "bpm": round(bpm_value, 2),
        "source": source,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "quality": quality,
        "quality_score": round(quality_score, 4),
        "quality_reason": quality_reason,
        "anomaly": anomaly,
        "anomaly_score": anomaly_score,
        "anomaly_reason": anomaly_reason,
        "features": {
            "fps": round(features["fps"], 4) if features["fps"] is not None else None,
            "amplitude": round(features["amplitude"], 6) if features["amplitude"] is not None else None,
            "regularity": round(features["regularity"], 4) if features["regularity"] is not None else None,
        },
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {WORKER_TOKEN}"},
            timeout=5,
        )

        if resp.status_code == 201:
            print(f"[worker] Da gui BPM={bpm_value:.2f}")

        else:
            print(resp.text)

    except requests.exceptions.RequestException as e:
        print(e)
def main():
    args = parse_args()
    cap, is_espcam = open_capture(args)

    model = YOLO("yolo11n-pose.pt")
    roi_extractor = ROIExtractor()

    tracker = MotionTracker(blur_kernel=(7, 7) if is_espcam else (5, 5))
    anomaly_detector = AnomalyDetector()

    current_roi = None
    frame_idx = 0

    fig = None
    raw_line = filtered_line = ax = None
    if not args.headless:
        plt.ion()
        fig, ax = plt.subplots(figsize=(10, 5))
        raw_line, = ax.plot([], [], alpha=0.5, label="Raw Signal")
        filtered_line, = ax.plot([], [], linewidth=2, label="Filtered Signal")
        ax.set_title("Respiration Signal Analysis")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Vertical Motion")
        ax.legend()
        ax.grid(True)
        try:
            fig.canvas.manager.set_window_title("Breathing Signal Analysis")
        except Exception:
            pass
        fig.show()

    block_signal = []
    block_start_time = time.time()

    fps_counter = 0
    fps_window_start = time.time()
    source_label = f"ESP32-CAM ({args.espcam})" if is_espcam else f"camera laptop so {args.camera}"
    source_kind = "esp32cam" if is_espcam else "webcam"
    print(f"[worker] Bat dau do nhip tho qua {source_label}")
    print(f"[worker] Khoi {args.interval:.0f} giay, Esc de dung")

    pose_overlay = None
    pose_status = "DANG TIM POSE"
    last_pose_status = None
    flow_status = "OPTICAL FLOW: CHUA CO ROI"

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                if is_espcam:
                    print("[worker] Mat ket noi ESP32-CAM, dang thu ket noi lai...")
                    cap.release()
                    cap = reopen_espcam(args.espcam)
                    fps_counter = 0
                    fps_window_start = time.time()
                    continue
                print("[worker] Camera laptop khong tra frame, dang thu lai...")
                time.sleep(0.5)
                continue

            frame_idx += 1
            fps_counter += 1

            elapsed_fps = time.time() - fps_window_start
            if elapsed_fps >= 10.0:
                actual_fps = fps_counter / elapsed_fps
                if is_espcam and actual_fps < MIN_ACCEPTABLE_FPS:
                    print(
                        f"[worker] CANH BAO: FPS trung binh {actual_fps:.1f} < {MIN_ACCEPTABLE_FPS}. "
                        "Tin hieu co the khong du de loc bandpass chinh xac. "
                        "Thu: (1) giam jpeg_quality trong firmware, (2) chuyen sang QVGA."
                    )
                fps_counter = 0
                fps_window_start = time.time()

            display_frame = frame.copy()
            should_update_roi = (current_roi is None) or (frame_idx % args.roi_update_every == 0)

            if should_update_roi:
                detected, pose_result, pose_status = detect_chest_roi(model, roi_extractor, frame)
                try:
                    pose_overlay = pose_result.plot(
                        img=frame.copy(), boxes=False, labels=False, conf=False
                    )
                except Exception:
                    pose_overlay = frame.copy()
                if pose_status != last_pose_status:
                    print(f"[worker] POSE/ROI: {pose_status}")
                    last_pose_status = pose_status
                if detected is not None:
                    was_none = current_roi is None
                    current_roi = smooth_roi(current_roi, detected, args.roi_smoothing)
                    if was_none:
                        print("[worker] Da phat hien vung nguc, bat dau theo doi")

            if pose_overlay is not None:
                display_frame = pose_overlay.copy()

            if current_roi is not None:
                x1, y1, x2, y2 = current_roi
                roi = frame[y1:y2, x1:x2]
                motion = tracker.process(roi)
                flow_status = "OPTICAL FLOW: DANG KHOI TAO"

                if motion is not None:
                    block_signal.append((time.time(), motion))
                    tracker.draw_particles(
                        display_frame,
                        (x1, y1, x2, y2),
                    )
                    cv2.putText(
                        display_frame, f"Motion: {motion:.6f}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                    )
                    flow_status = (
                        f"OPTICAL FLOW: {motion:+.5f} | {tracker.phase_label()}"
                    )

                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    display_frame, "CHEST ROI", (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2
                )
            else:
                flow_status = "OPTICAL FLOW: CHUA CO ROI NGUC"

            pose_color = (0, 200, 0) if current_roi is not None else (0, 165, 255)
            cv2.putText(
                display_frame, f"POSE: {pose_status}", (20, 26),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, pose_color, 2
            )
            cv2.putText(
                display_frame, flow_status, (20, 142),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2
            )

            cv2.putText(
                display_frame, "ESP32-CAM" if is_espcam else "LAPTOP CAMERA",
                (20, display_frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1
            )
            cv2.putText(
                display_frame, "HIT VAO", (20, 68),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2
            )
            cv2.putText(
                display_frame, "THO RA", (20, 92),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 0), 2
            )
            cv2.putText(
                display_frame, f"PHA: {tracker.phase_label()}", (20, 116),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, tracker.phase_color_now(), 2
            )

            if not args.headless:
                cv2.imshow("Chest ROI", display_frame)
                key = cv2.waitKey(1)
                if key == 27:
                    break

            if fig is not None and plt.fignum_exists(fig.number):
                fig.canvas.flush_events()

            now = time.time()
            if now - block_start_time >= args.interval:
                if len(block_signal) >= 10:
                    block_quality = assess_block_quality(block_signal)
                    if not block_quality["valid"]:
                        print(f"[worker] BO QUA BLOCK: {block_quality['reason']}; khong tao measurement")
                        block_signal = []
                        block_start_time = now
                        continue

                    timestamps = block_quality["timestamps"]
                    values = block_quality["values"]
                    duration = block_quality["duration"]
                    actual_fps_block = block_quality["fps"]

                    try:
                        filtered_signal = SignalFilter.smooth(
                            values, timestamps=timestamps, duration_seconds=duration
                        )
                        bpm, peaks = BreathingRateEstimator.estimate(filtered_signal, duration)
                    except Exception as e:
                        print(
                            f"[worker] LOI khi tinh BPM cho khoi nay, BO QUA khoi "
                            f"va tiep tuc: {type(e).__name__}: {e}"
                        )
                        block_signal = []
                        block_start_time = now
                        continue

                    quality, quality_score, quality_reason, amplitude, regularity = summarize_signal_quality(
                        filtered_signal,
                        peaks,
                        actual_fps_block,
                    )
                    anomaly_features = {
                        "bpm": bpm,
                        "fps": actual_fps_block,
                        "amplitude": amplitude,
                        "regularity": regularity,
                        "quality_score": quality_score,
                    }
                    anomaly_result = anomaly_detector.predict(anomaly_features)
                    anomaly_detector.observe(anomaly_features)
                    push_bpm(
                        args.api,
                        bpm,
                        display_frame.copy(),
                        source_kind,
                        quality,
                        quality_score,
                        quality_reason,
                        {
                            "fps": actual_fps_block,
                            "amplitude": amplitude,
                            "regularity": regularity,
                        },
                        anomaly=anomaly_result["anomaly"],
                        anomaly_score=anomaly_result["anomaly_score"],
                        anomaly_reason=anomaly_result["reason"],
                    )
                    print(
                        f"[worker] Respiration Rate: {bpm:.2f} BPM "
                        f"(fps={actual_fps_block:.1f}, frames={len(values)}, duration={duration:.1f}s)"
                    )

                    if fig is not None and plt.fignum_exists(fig.number):
                        x_raw = [t - timestamps[0] for t in timestamps]
                        if len(filtered_signal) == len(x_raw):
                            x_filtered = x_raw
                        else:
                            x_filtered = np.linspace(0, duration, len(filtered_signal))
                        raw_line.set_data(x_raw, values)
                        filtered_line.set_data(x_filtered, filtered_signal)
                        ax.relim()
                        ax.autoscale_view()
                        fig.canvas.draw()
                        fig.canvas.flush_events()
                else:
                    print(
                        f"[worker] BO QUA BLOCK: insufficient_samples={len(block_signal)}; "
                        "khong tao measurement"
                    )

                block_signal = []
                block_start_time = now

    except KeyboardInterrupt:
        print("[worker] Da dung theo yeu cau (Ctrl+C)")
    finally:
        cap.release()
        if not args.headless:
            cv2.destroyAllWindows()
        if fig is not None:
            plt.close(fig)


if __name__ == "__main__":
    main()
