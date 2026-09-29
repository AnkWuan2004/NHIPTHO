from datetime import datetime, timezone


def measurement_payload(bpm=31.0):
    return {
        "bpm": bpm,
        "source": "webcam",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "quality": "valid",
        "quality_score": 0.9,
        "quality_reason": "smoke fixture",
        "anomaly": "unknown",
        "anomaly_score": None,
        "anomaly_reason": None,
        "features": {
            "fps": 12.0,
            "amplitude": 0.2,
            "regularity": 0.9,
        },
    }


def test_caregiver_measurement_alert_history_flow(api_client):
    health = api_client.get("/healthz")
    assert health.status_code == 200
    assert health.get_json()["database"] == "ok"

    login = api_client.post(
        "/api/auth/login",
        json={"username": "caregiver", "password": "demo-password"},
    )
    assert login.status_code == 200
    assert api_client.get("/").status_code == 200

    created = api_client.post(
        "/api/measurements",
        json=measurement_payload(),
        headers={"Authorization": "Bearer test-worker-token"},
    )
    assert created.status_code == 201
    measurement = created.get_json()
    assert measurement["bpm"] == 31.0
    assert measurement["alert_id"] is not None

    latest = api_client.get("/api/latest")
    assert latest.status_code == 200
    assert latest.get_json()["id"] == measurement["id"]

    history = api_client.get("/api/history?limit=10&source=webcam")
    assert history.status_code == 200
    assert history.get_json()["items"][0]["id"] == measurement["id"]

    alerts = api_client.get("/api/alerts?limit=10")
    assert alerts.status_code == 200
    assert alerts.get_json()["items"][0]["measurement_id"] == measurement["id"]

    logout = api_client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert api_client.get("/api/latest").status_code == 401


def test_worker_push_payload_matches_measurement_contract(monkeypatch):
    import numpy as np

    from breathing_worker import push_bpm

    captured = {}

    class FakeResponse:
        status_code = 201
        text = "created"

    def fake_post(url, json, headers, timeout):
        captured.update({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("breathing_worker.requests.post", fake_post)
    push_bpm(
        "http://127.0.0.1:5000",
        18.5,
        np.zeros((8, 8, 3), dtype=np.uint8),
        "webcam",
        "valid",
        0.9,
        "smoke fixture",
        {"fps": 12.0, "amplitude": 0.2, "regularity": 0.9},
        anomaly="unknown",
        anomaly_score=None,
        anomaly_reason=None,
    )

    assert captured["url"] == "http://127.0.0.1:5000/api/measurements"
    assert captured["headers"]["Authorization"].startswith("Bearer ")
    assert captured["json"]["source"] == "webcam"
    assert captured["json"]["features"]["fps"] == 12.0
