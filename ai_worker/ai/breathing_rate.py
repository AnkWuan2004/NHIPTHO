import numpy as np
from scipy.signal import find_peaks


class BreathingRateEstimator:
    """
    Dem peak tren tin hieu da loc de tinh BPM.

    Ban cu dung distance=50 CO DINH THEO SAMPLE (khong theo thoi gian),
    va KHONG co nguong bien do (prominence/height) -- nen bat ky gon
    nhieu nho nao cung duoc tinh ngang hang voi 1 nhip tho thuc, gay
    "nhay so" giua cac lan do.

    Ban moi: distance tinh theo THOI GIAN THUC (tu fps = len(signal)/
    duration_seconds), va them prominence -- chi tinh la peak khi noi
    bat ro rang so voi muc dao dong chung cua tin hieu.

    FIX: dung np.atleast_1d() thay vi np.asarray() truc tiep de tranh
    loi "TypeError: len() of unsized object" khi tham so signal truyen
    vao vo tinh la scalar hoac mang 0-chieu (co the xay ra neu ham loc
    phia truoc tra ve gia tri khong dung dang, dac biet o fps rat
    thap/khong on dinh nhu ESP32-CAM qua WiFi yeu).
    """

    MAX_PLAUSIBLE_BPM = 40
    MIN_SECONDS_BETWEEN_BREATHS = 60.0 / MAX_PLAUSIBLE_BPM

    PROMINENCE_FACTOR = 0.3
    MIN_VALID_PEAKS = 2

    @staticmethod
    def estimate(signal, duration_seconds):
        signal = np.atleast_1d(np.asarray(signal, dtype=float))

        if signal.size < 3 or duration_seconds is None or duration_seconds <= 0:
            return 0.0, []

        if not np.all(np.isfinite(signal)):
            signal = signal[np.isfinite(signal)]
            if signal.size == 0:
                return 0.0, []

        fps = signal.size / duration_seconds
        min_distance_samples = max(
            1,
            int(fps * BreathingRateEstimator.MIN_SECONDS_BETWEEN_BREATHS)
        )
        min_distance_samples = min(min_distance_samples, max(1, signal.size - 1))

        signal_std = float(np.std(signal))
        prominence = (
            BreathingRateEstimator.PROMINENCE_FACTOR * signal_std
            if signal_std > 0 else None
        )

        peaks, _ = find_peaks(
            signal,
            distance=min_distance_samples,
            prominence=prominence,
        )

        breaths = len(peaks)
        if breaths == 0:
            return 0.0, peaks

        if breaths >= BreathingRateEstimator.MIN_VALID_PEAKS:
            intervals = np.diff(peaks).astype(float) / fps
            intervals = intervals[intervals > 0]
            bpm = 60.0 / float(np.median(intervals)) if intervals.size else 0.0
        else:
            bpm = (breaths / duration_seconds) * 60.0

        return bpm, peaks
