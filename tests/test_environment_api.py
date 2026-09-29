from datetime import datetime, timedelta, timezone


def login(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "caregiver", "password": "demo-password"},
    )
    assert response.status_code == 200


def measurement_payload(bpm, stamp):
    return {
        "bpm": bpm,
        "source": "webcam",
        "measured_at": stamp,
        "quality": "valid",
        "quality_score": 0.9,
        "quality_reason": "environment fixture",
        "anomaly": "normal",
        "anomaly_score": 0.1,
        "anomaly_reason": "fixture",
        "features": {"fps": 12.0, "amplitude": 0.2, "regularity": 0.9},
    }


def environment_payload(device_id, temperature, humidity, stamp):
    return {
        "device_id": device_id,
        "temperature_c": temperature,
        "humidity_pct": humidity,
        "measured_at": stamp,
    }


def device_post(client, payload, token="local-device-token"):
    return client.post(
        "/api/environment/readings",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def worker_post(client, payload):
    return client.post(
        "/api/measurements",
        json=payload,
        headers={"Authorization": "Bearer test-worker-token"},
    )


def test_environment_auth_and_temperature_alarm(api_client):
    assert api_client.get("/api/environment/latest").status_code == 401
    payload = environment_payload(
        "devkit-01", 25.0, 55.0, datetime.now(timezone.utc).isoformat()
    )
    assert device_post(api_client, payload, token="wrong-token").status_code == 401
    assert device_post(api_client, payload).status_code == 201

    login(api_client)
    latest = api_client.get("/api/environment/latest")
    assert latest.status_code == 200
    assert latest.get_json()["alarm"]["active"] is False

    high = device_post(
        api_client,
        environment_payload(
            "devkit-01", 31.0, 55.0,
            (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
        ),
    )
    assert high.status_code == 201
    body = high.get_json()
    assert body["temperature_c"] == 31.0
    assert body["alarm"]["active"] is True
    assert body["alarm"]["reasons"] == ["temperature_high"]
    assert body["alarm"]["severity"] == "warning"
    assert body["alarm"]["buzzer"] is True
    assert body["alarm"]["led"] == "red"
    assert body["alarm"]["temperature_high_c"] == 30.0


def test_environment_combines_fresh_bpm(api_client):
    now = datetime.now(timezone.utc)
    fresh_bpm = worker_post(
        api_client,
        measurement_payload(31.0, now.isoformat()),
    )
    assert fresh_bpm.status_code == 201

    breathing_alarm = device_post(
        api_client,
        environment_payload(
            "devkit-02", 25.0, 60.0,
            (now + timedelta(seconds=1)).isoformat(),
        ),
    )
    assert breathing_alarm.status_code == 201
    alarm = breathing_alarm.get_json()["alarm"]
    assert alarm["reasons"] == ["breathing_high"]
    assert alarm["severity"] == "critical"
    assert alarm["bpm_stale"] is False

def test_environment_suppresses_stale_bpm(api_client):
    now = datetime.now(timezone.utc)
    stale_bpm = worker_post(
        api_client,
        measurement_payload(31.0, (now - timedelta(seconds=121)).isoformat()),
    )
    assert stale_bpm.status_code == 201
    stale_alarm = device_post(
        api_client,
        environment_payload(
            "devkit-02", 31.0, 60.0,
            (now + timedelta(seconds=2)).isoformat(),
        ),
    )
    assert stale_alarm.status_code == 201
    stale = stale_alarm.get_json()["alarm"]
    assert stale["reasons"] == ["temperature_high"]
    assert stale["bpm_stale"] is True


def test_environment_validation_and_duplicate(api_client):
    payload = environment_payload(
        "devkit-03", 25.0, 50.0, datetime.now(timezone.utc).isoformat()
    )
    assert device_post(api_client, {**payload, "humidity_pct": 101}).status_code == 422
    assert device_post(api_client, {**payload, "temperature_c": 81}).status_code == 422
    assert device_post(api_client, payload).status_code == 201
    assert device_post(api_client, payload).status_code == 409
