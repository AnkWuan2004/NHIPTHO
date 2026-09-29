import os
import tempfile

from ai_worker.ai.anomaly_detector import AnomalyDetector


def baseline_features(index):
    return {
        "bpm": 18.0 + (index % 5) * 0.15,
        "fps": 12.0 + (index % 3) * 0.1,
        "amplitude": 0.18 + (index % 4) * 0.01,
        "regularity": 0.88 + (index % 4) * 0.01,
        "quality_score": 0.88 + (index % 3) * 0.02,
    }


def test_warmup_returns_unknown_then_persists_model():
    with tempfile.TemporaryDirectory(prefix="anomaly-detector-") as directory:
        model_path = os.path.join(directory, "model.joblib")
        detector = AnomalyDetector(model_path=model_path, min_samples=20)
        assert detector.predict(baseline_features(0))["anomaly"] == "unknown"

        for index in range(20):
            detector.observe(baseline_features(index))

        assert os.path.exists(model_path)
        assert detector.predict(baseline_features(21))["anomaly"] == "normal"

        reloaded = AnomalyDetector(model_path=model_path, min_samples=20)
        assert reloaded.predict(baseline_features(22))["anomaly"] == "normal"


def test_injected_outliers_are_detected():
    with tempfile.TemporaryDirectory(prefix="anomaly-detector-") as directory:
        detector = AnomalyDetector(
            model_path=os.path.join(directory, "model.joblib"),
            min_samples=20,
        )
        detector.fit([baseline_features(index) for index in range(60)])
        outliers = [
            {
                "bpm": 70.0 + index,
                "fps": 2.0,
                "amplitude": 8.0,
                "regularity": 0.05,
                "quality_score": 0.1,
            }
            for index in range(20)
        ]
        labels = [detector.predict(item)["anomaly"] for item in outliers]
        anomaly_ratio = labels.count("anomaly") / len(labels)
        assert anomaly_ratio >= 0.90


def test_invalid_features_are_unknown_not_an_exception():
    with tempfile.TemporaryDirectory(prefix="anomaly-detector-") as directory:
        detector = AnomalyDetector(model_path=os.path.join(directory, "model.joblib"))
        result = detector.predict({"bpm": 18.0})
        assert result["anomaly"] == "unknown"
        assert result["anomaly_score"] is None
        assert result["reason"]
