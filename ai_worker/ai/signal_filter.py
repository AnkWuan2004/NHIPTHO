import numpy as np
from scipy.signal import butter, filtfilt, savgol_filter


class SignalFilter:
    """
    Loc tin hieu motion ve dung dai tan nhip tho nguoi thuc te:
    ~6-30 lan/phut tuong duong 0.1-0.5 Hz.

    Ban cu dung Savitzky-Golay voi window_length=21 SAMPLE CO DINH.
    O ~20-30 FPS, 21 sample chi la ~0.7-1 giay -- ngan hon ca 1/4 chu
    ky tho thuc (3-5 giay) -- nen gan nhu khong loc duoc nhieu tan so
    cao, va cung khong loai duoc troi nen tan so thap. Ban moi nay
    dung bandpass Butterworth, tu tinh sample rate thuc te (fps) tu
    chinh du lieu thay vi gia dinh co dinh.

    FIX (quan trong): mot so phien ban scipy/numpy, khi filtfilt()
    chay voi input rat ngan sat nguong padlen, co the tra ve mang
    0-chieu (0-d array) hoac gia tri khong dung dang mang 1 chieu ma
    ham goi phia sau (BreathingRateEstimator.estimate) khong luong
    truoc -- gay loi "TypeError: len() of unsized object". Ham nay
    now LUON validate ket qua bang np.atleast_1d() va kiem tra
    shape/length khop voi input truoc khi tra ve, neu khong hop le se
    coi nhu that bai va roi ve nhanh fallback an toan hon.
    """

    LOW_HZ = 0.1
    HIGH_HZ = 0.5
    MIN_FPS = 5.0

    @staticmethod
    def smooth(signal, timestamps=None, fps=None, duration_seconds=None):
        """
        signal: tin hieu motion thoi gian.
        timestamps: (tuy chon nhung KHUYEN NGHI dung) mang thoi diem
            thuc te (giay, vd time.time()) cua tung sample. Neu co,
            se RESAMPLE tin hieu ve luoi thoi gian DEU truoc khi loc
            bandpass -- vi fps thuc te thuong khong deu (do YOLO chay
            xen ke, mang WiFi cua ESP32-CAM giat cuc), va bo loc tan
            so (bandpass) chi dung khi sample cach deu nhau.
        fps: so sample/giay (uu tien dung truc tiep neu co va khong
            co timestamps).
        duration_seconds: neu khong co fps/timestamps, se tu tinh
            fps = len(signal) / duration_seconds (kem chinh xac hon
            vi gia dinh sample deu nhau).

        Neu khong du du lieu de loc bandpass on dinh, fallback ve
        Savitzky-Golay (nhu ban cu) hoac tra nguyen tin hieu goc.
        Luon tra ve mang numpy 1 chieu co CUNG DO DAI voi tin hieu
        dau vao (sau khi resample neu co).
        """
        signal = np.atleast_1d(np.asarray(signal, dtype=float))

        if signal.size == 0:
            return signal

        if not np.all(np.isfinite(signal)):
            signal = signal[np.isfinite(signal)]
            if signal.size == 0:
                return signal

        if timestamps is not None:
            timestamps = np.atleast_1d(np.asarray(timestamps, dtype=float))
            if timestamps.size != signal.size or timestamps.size < 2:
                timestamps = None
            elif timestamps.size >= 2:
                finite = np.isfinite(timestamps) & np.isfinite(signal)
                timestamps = timestamps[finite]
                signal = signal[finite]
                if signal.size < 2 or np.any(np.diff(timestamps) <= 0):
                    timestamps = None
            if timestamps is not None and timestamps.size >= 2:
                duration = float(timestamps[-1] - timestamps[0])
                if duration > 0:
                    target_fps = (signal.size - 1) / duration
                    if target_fps < SignalFilter.MIN_FPS:
                        return signal
                    n_uniform = max(2, int(duration * target_fps))
                    uniform_t = np.linspace(timestamps[0], timestamps[-1], n_uniform)
                    signal = np.interp(uniform_t, timestamps, signal)
                    fps = target_fps

        if fps is None and duration_seconds:
            fps = max(0.0, (signal.size - 1) / duration_seconds)

        if fps and fps >= SignalFilter.MIN_FPS and signal.size > 30:
            filtered = SignalFilter._bandpass(signal, fps)
            if filtered is not None:
                filtered = np.atleast_1d(filtered)
                if filtered.ndim == 1 and filtered.size == signal.size:
                    return filtered

        if signal.size < 21:
            return signal

        smoothed = savgol_filter(signal, window_length=21, polyorder=3)
        return np.atleast_1d(smoothed)

    @staticmethod
    def _bandpass(signal, fps):
        nyquist = fps / 2.0
        low = SignalFilter.LOW_HZ / nyquist
        high = SignalFilter.HIGH_HZ / nyquist

        if high >= 1.0:
            high = 0.99
        if low <= 0:
            low = 1e-4
        if low >= high:
            return None

        try:
            b, a = butter(N=3, Wn=[low, high], btype="band")
            padlen = 3 * max(len(a), len(b))
            if signal.size <= padlen:
                return None
            result = filtfilt(b, a, signal)
            result = np.atleast_1d(result)
            if result.ndim != 1 or result.size != signal.size:
                return None
            return result
        except Exception:
            return None
