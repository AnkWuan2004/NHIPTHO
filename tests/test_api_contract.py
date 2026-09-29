from datetime import datetime, timezone


def login(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "caregiver", "password": "demo-password"},
    )
    assert response.status_code == 200
    assert response.get_json() == {
        "authenticated": True,
        "user": {"username": "caregiver"},
    }


def measurement_payload(bpm=18.0, source="webcam", stamp=None, anomaly="normal"):
    stamp = stamp or datetime.now(timezone.utc).isoformat()
    return {
        "bpm": bpm,
        "source": source,
        "measured_at": stamp,
        "quality": "valid",
        "quality_score": 0.9,
        "quality_reason": "contract fixture",
        "anomaly": anomaly,
        "anomaly_score": 0.2 if anomaly != "unknown" else None,
        "anomaly_reason": "fixture",
        "features": {
            "fps": 12.0,
            "amplitude": 0.2,
            "regularity": 0.9,
        },
    }


def worker_post(client, payload):
    return client.post(
        "/api/measurements",
        json=payload,
        headers={"Authorization": "Bearer test-worker-token"},
    )


def unauthenticated_worker_post(client, payload):
    return client.post("/api/measurements", json=payload)


def test_public_auth_and_protected_contract(api_client):
    health = api_client.get("/healthz")
    assert health.status_code == 200
    assert health.get_json()["status"] == "ok"
    assert health.get_json()["database"] == "ok"

    login_page = api_client.get("/login")
    assert login_page.status_code == 200
    assert "Đăng nhập caregiver" in login_page.get_data(as_text=True)
    assert api_client.get("/").status_code == 302

    for path in ("/api/me", "/api/latest", "/api/history", "/api/alerts", "/api/settings/thresholds"):
        assert api_client.get(path).status_code == 401
    assert api_client.post("/api/auth/logout").status_code == 401
    assert api_client.post("/api/auth/login", json={"username": "caregiver"}).status_code == 400
    assert api_client.post(
        "/api/auth/login",
        json={"username": "caregiver", "password": "wrong"},
    ).status_code == 401

    login(api_client)
    me = api_client.get("/api/me")
    assert me.status_code == 200
    assert me.get_json() == {"authenticated": True, "user": {"username": "caregiver"}}
    assert api_client.post("/api/auth/logout").get_json() == {"authenticated": False}
    assert api_client.get("/api/me").status_code == 401


def test_measurement_history_and_anomaly_contract(api_client):
    login(api_client)
    empty_history = api_client.get("/api/history")
    assert empty_history.status_code == 200
    assert empty_history.get_json() == {"items": [], "limit": 100}

    assert api_client.get("/api/history?limit=0").status_code == 400
    assert api_client.get("/api/alerts?limit=0").status_code == 400
    assert unauthenticated_worker_post(api_client, measurement_payload(bpm=18.0)).status_code == 401
    assert worker_post(api_client, measurement_payload(bpm=0.0)).status_code == 422

    stamp = "2026-09-27T12:00:00+00:00"
    created = worker_post(
        api_client,
        measurement_payload(bpm=18.4, stamp=stamp, anomaly="anomaly"),
    )
    assert created.status_code == 201
    body = created.get_json()
    assert body["source"] == "webcam"
    assert body["anomaly"] == "anomaly"
    assert body["anomaly_score"] == 0.2
    assert body["anomaly_reason"] == "fixture"
    assert set(("id", "bpm", "measured_at", "quality", "features", "alert_id")) <= set(body)

    latest = api_client.get("/api/latest")
    assert latest.status_code == 200
    assert latest.get_json()["id"] == body["id"]
    history = api_client.get("/api/history?limit=10&source=webcam")
    assert history.status_code == 200
    assert history.get_json()["items"][0]["anomaly"] == "anomaly"
    assert api_client.get("/").status_code == 200
    assert worker_post(api_client, measurement_payload(bpm=18.4, stamp=stamp)).status_code == 409


def test_threshold_settings_and_alert_contract(api_client):
    login(api_client)
    defaults = api_client.get("/api/settings/thresholds")
    assert defaults.status_code == 200
    assert defaults.get_json() == {
        "low": 5.0,
        "high": 25.0,
        "temperature_high_c": 30.0,
        "consecutive_required": 1,
        "cooldown_seconds": 300,
    }

    updated = api_client.put(
        "/api/settings/thresholds",
        json={"low": 6, "high": 26, "temperature_high_c": 31, "consecutive_required": 1, "cooldown_seconds": 60},
    )
    assert updated.status_code == 200
    assert updated.get_json()["low"] == 6.0
    assert updated.get_json()["temperature_high_c"] == 31.0
    assert api_client.put(
        "/api/settings/thresholds",
        json={"low": 30, "high": 25, "consecutive_required": 1, "cooldown_seconds": 30},
    ).status_code == 422

    first = worker_post(
        api_client,
        measurement_payload(bpm=31, stamp="2026-09-27T12:01:00+00:00", anomaly="unknown"),
    )
    second = worker_post(
        api_client,
        measurement_payload(bpm=32, stamp="2026-09-27T12:02:00+00:00", anomaly="unknown"),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json()["alert_id"] is not None
    assert second.get_json()["alert_id"] == first.get_json()["alert_id"]

    alerts = api_client.get("/api/alerts")
    assert alerts.status_code == 200
    assert len(alerts.get_json()["items"]) == 1
    assert alerts.get_json()["items"][0]["status"] == "created"
