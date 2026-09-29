import numpy as np

from ai_worker.ai.breathing_rate import BreathingRateEstimator
from ai_worker.ai.roi_extractor import ROIExtractor
from ai_worker.ai.signal_filter import SignalFilter
from ai_worker.ai.pose_detector import PoseDetector
from ai_worker.ai.motion_tracker import MotionTracker
from ai_worker.breathing_worker import assess_block_quality, summarize_signal_quality


class FakeKeypoints:
    def __init__(self, xy, conf=None):
        self.xy = xy
        self.conf = conf


class FakeResult:
    def __init__(self, xy, conf=None):
        self.keypoints = FakeKeypoints(xy, conf)


def test_synthetic_breathing_signal_has_stable_bpm_and_quality():
    fps = 20.0
    duration = 60.0
    timestamps = np.arange(0.0, duration, 1.0 / fps)
    signal = np.sin(2 * np.pi * 0.2 * timestamps)
    signal += 0.03 * np.sin(2 * np.pi * 1.7 * timestamps)

    filtered = SignalFilter.smooth(signal, timestamps=timestamps, duration_seconds=duration)
    bpm, peaks = BreathingRateEstimator.estimate(filtered, duration)
    quality, score, reason, amplitude, regularity = summarize_signal_quality(filtered, peaks, fps)

    assert 10.5 <= bpm <= 13.5
    assert quality == "valid"
    assert 0.0 <= score <= 1.0
    assert reason
    assert amplitude > 0
    assert 0.0 <= regularity <= 1.0


def test_invalid_blocks_are_named_and_never_become_zero_measurements():
    assert assess_block_quality([])["reason"] == "insufficient_samples=0"

    low_fps = [(index * 0.5, 0.1) for index in range(30)]
    assert assess_block_quality(low_fps)["reason"].startswith("low_fps=")

    excessive_motion = [(index * 0.1, 20.0 if index % 2 else -20.0) for index in range(100)]
    assert assess_block_quality(excessive_motion)["reason"].startswith("excessive_motion_amplitude=")

    assert BreathingRateEstimator.estimate(np.zeros(2), 1.0)[0] == 0.0


def test_roi_and_pose_selection_reject_weak_geometry_and_choose_confident_person():
    extractor = ROIExtractor()
    frame_shape = (480, 640, 3)
    valid_roi = extractor.get_chest_roi(
        np.zeros(frame_shape, dtype=np.uint8),
        np.array([250, 150]),
        np.array([390, 150]),
        np.array([260, 350]),
        np.array([380, 350]),
    )
    assert valid_roi is not None
    assert extractor.validate_roi(frame_shape, valid_roi)
    assert extractor.get_chest_roi(
        np.zeros(frame_shape, dtype=np.uint8),
        np.array([10, 10]),
        np.array([15, 10]),
        np.array([10, 15]),
        np.array([15, 15]),
    ) is None

    weak = np.zeros((17, 2), dtype=float)
    confident = weak.copy()
    confident[[5, 6, 11, 12]] = [[250, 150], [390, 150], [260, 350], [380, 350]]
    xy = np.stack([confident, confident])
    conf = np.full((2, 17), 0.9)
    conf[0, [5, 6, 11, 12]] = 0.2

    selected = PoseDetector.select_best_person(FakeResult(xy, conf))
    assert selected is not None
    np.testing.assert_allclose(selected[[5, 6, 11, 12]], confident[[5, 6, 11, 12]])


def test_low_fps_filter_does_not_invent_a_regular_sample_rate():
    timestamps = np.arange(30, dtype=float) / 2.0
    signal = np.sin(2 * np.pi * 0.2 * timestamps)
    filtered = SignalFilter.smooth(signal, timestamps=timestamps, duration_seconds=timestamps[-1])
    np.testing.assert_allclose(filtered, signal)


def test_optical_flow_colors_inhale_red_and_exhale_green():
    assert MotionTracker.phase_color(-0.2) == (0, 0, 255)
    assert MotionTracker.phase_color(0.2) == (0, 200, 0)
