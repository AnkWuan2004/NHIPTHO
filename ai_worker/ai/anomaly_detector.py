import os

import numpy as np
from joblib import dump, load
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = ("bpm", "fps", "amplitude", "regularity", "quality_score")


class AnomalyDetector:
    """Warm-up Isolation Forest over the measurement feature vector."""

    def __init__(self, model_path=None, min_samples=20, contamination=0.1):
        default_path = os.path.join(os.path.dirname(__file__), "anomaly_model.joblib")
        self.model_path = model_path or os.getenv("BREATHING_ANOMALY_MODEL_PATH", default_path)
        self.min_samples = int(min_samples)
        self.contamination = float(contamination)
        self.model = None
        self.scaler = None
        self.sample_count = 0
        self._baseline = []
        self.load()

    @staticmethod
    def vectorize(features):
        if not isinstance(features, dict):
            raise ValueError("features phải là object")
        values = []
        for name in FEATURE_NAMES:
            value = features.get(name)
            if value is None or not np.isfinite(float(value)):
                raise ValueError(f"features.{name} phải là số hữu hạn")
            values.append(float(value))
        return np.asarray(values, dtype=float)

    def fit(self, baseline):
        matrix = np.asarray([self.vectorize(item) for item in baseline], dtype=float)
        if matrix.ndim != 2 or len(matrix) < self.min_samples:
            return False

        self.scaler = StandardScaler()
        scaled_matrix = self.scaler.fit_transform(matrix)
        self.model = IsolationForest(
            n_estimators=300,
            contamination=self.contamination,
            random_state=42,
        )
        self.model.fit(scaled_matrix)
        self.sample_count = len(matrix)
        self._baseline = []
        self.save()
        return True

    def observe(self, features):
        """Add a warm-up sample and fit once the minimum baseline is reached."""
        vector = self.vectorize(features)
        if self.model is not None:
            return False
        self._baseline.append(vector.tolist())
        if len(self._baseline) < self.min_samples:
            self.sample_count = len(self._baseline)
            return False
        return self.fit([dict(zip(FEATURE_NAMES, row)) for row in self._baseline])

    def predict(self, features):
        try:
            vector = self.vectorize(features).reshape(1, -1)
        except (TypeError, ValueError) as exc:
            return {
                "anomaly": "unknown",
                "anomaly_score": None,
                "reason": f"invalid_features: {exc}",
            }

        if self.model is None:
            return {
                "anomaly": "unknown",
                "anomaly_score": None,
                "reason": f"warmup: {self.sample_count}/{self.min_samples} baseline samples",
            }

        if self.scaler is None:
            return {
                "anomaly": "unknown",
                "anomaly_score": None,
                "reason": "model_scaler_missing",
            }

        scaled_vector = self.scaler.transform(vector)
        prediction = int(self.model.predict(scaled_vector)[0])
        score = float(-self.model.decision_function(scaled_vector)[0])
        return {
            "anomaly": "anomaly" if prediction == -1 else "normal",
            "anomaly_score": score,
            "reason": "isolation_forest",
        }

    def save(self):
        if self.model is None:
            return
        directory = os.path.dirname(os.path.abspath(self.model_path))
        os.makedirs(directory, exist_ok=True)
        dump({
            "model": self.model,
            "scaler": self.scaler,
            "sample_count": self.sample_count,
            "feature_names": FEATURE_NAMES,
        }, self.model_path)

    def load(self):
        if not self.model_path or not os.path.exists(self.model_path):
            return False
        try:
            payload = load(self.model_path)
            if tuple(payload.get("feature_names", ())) != FEATURE_NAMES:
                return False
            self.model = payload["model"]
            self.scaler = payload["scaler"]
            self.sample_count = int(payload.get("sample_count", 0))
            return True
        except (OSError, ValueError, KeyError, TypeError):
            self.model = None
            self.scaler = None
            self.sample_count = 0
            return False
