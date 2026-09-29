import os
import hmac
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import desc, text

from database import SessionLocal, ensure_schema
from models import Alert, BreathingRecord, EnvironmentReading, ThresholdSettings
from alarm_manager import (
    environment_alarm_decision,
    get_threshold_settings,
    process_measurement,
    threshold_settings_to_dict,
)
from auth import authenticate, caregiver_required, login_user, logout_user
from config import ALERT_TEMPERATURE_HIGH_C, APP_VERSION, BREATHING_DEVICE_TOKEN, SECRET_KEY

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "dashboard", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "dashboard", "static")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)
WORKER_TOKEN = os.getenv("BREATHING_WORKER_TOKEN", "local-worker-token")
ensure_schema()


@app.route("/healthz", methods=["GET"])
def healthz():
    """Return a small public liveness/readiness signal for local setup."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return jsonify({
            "status": "ok",
            "version": APP_VERSION,
            "database": "ok",
        }), 200
    except Exception:
        return jsonify({
            "status": "error",
            "version": APP_VERSION,
            "database": "error",
            "error": "database_unavailable",
        }), 503
    finally:
        db.close()


@app.route("/login", methods=["GET"])
def login():
    if session.get("caregiver_authenticated") is True:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "error": "INVALID_REQUEST",
            "message": "username và password là bắt buộc",
        }), 400

    db = SessionLocal()
    try:
        account, error = authenticate(db, username.strip(), password)
        if error == "rate_limited":
            return jsonify({
                "error": "RATE_LIMITED",
                "message": "Quá nhiều lần đăng nhập sai, thử lại sau 60 giây",
            }), 429
        if account is None:
            return jsonify({
                "error": "INVALID_CREDENTIALS",
                "message": "Tên đăng nhập hoặc mật khẩu không đúng",
            }), 401

        login_user(account)
        return jsonify({
            "authenticated": True,
            "user": {"username": account.username},
        }), 200
    finally:
        db.close()


@app.route("/api/auth/logout", methods=["POST"])
@caregiver_required
def api_logout():
    logout_user()
    return jsonify({"authenticated": False}), 200


@app.route("/api/me", methods=["GET"])
@caregiver_required
def api_me():
    return jsonify({
        "authenticated": True,
        "user": {"username": session.get("caregiver_username")},
    }), 200


def error_response(code, message, status):
    return jsonify({
        "error": code,
        "message": message,
        "details": None,
    }), status


def parse_measurement_time(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("measured_at phải là ISO-8601 có timezone")

    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("measured_at phải có timezone")
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _iso_timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def record_to_dict(record):
    measured_at = record.measured_at or record.created_at
    return {
        "id": record.id,
        "bpm": record.bpm,
        "source": record.source or "camera_ai",
        "measured_at": _iso_timestamp(measured_at),
        "quality": record.quality or "uncertain",
        "quality_score": record.quality_score,
        "quality_reason": record.quality_reason,
        "anomaly": record.anomaly or "unknown",
        "anomaly_score": record.anomaly_score,
        "anomaly_reason": record.anomaly_reason,
        "features": {
            "fps": record.feature_fps,
            "amplitude": record.feature_amplitude,
            "regularity": record.feature_regularity,
        },
        "alert_id": record.alert_id,
        "note": record.note,
    }


def alert_to_dict(alert):
    return {
        "id": alert.id,
        "measurement_id": alert.measurement_id,
        "kind": alert.kind,
        "status": alert.status,
        "bpm": alert.bpm,
        "message": alert.message,
        "created_at": _iso_timestamp(alert.created_at),
        "email_sent_at": _iso_timestamp(alert.email_sent_at),
    }


def worker_required(view):
    """Protect machine ingestion separately from the caregiver session."""
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied:
            supplied = request.headers.get("X-Worker-Token", "").strip()
        if not supplied or not hmac.compare_digest(supplied, WORKER_TOKEN):
            return error_response("WORKER_AUTH_REQUIRED", "Worker token không hợp lệ", 401)
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


def device_required(view):
    """Protect the DHT22 device write path with its own local token."""
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied:
            supplied = request.headers.get("X-Device-Token", "").strip()
        if not supplied or not hmac.compare_digest(supplied, BREATHING_DEVICE_TOKEN):
            return error_response("DEVICE_AUTH_REQUIRED", "Device token không hợp lệ", 401)
        return view(*args, **kwargs)

    wrapped.__name__ = view.__name__
    return wrapped


def validate_environment(data):
    if not isinstance(data, dict):
        return None, error_response("INVALID_REQUEST", "Body JSON không hợp lệ", 400)

    device_id = data.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip() or len(device_id.strip()) > 64:
        return None, error_response("INVALID_DEVICE_ID", "device_id phải là chuỗi không quá 64 ký tự", 400)

    try:
        temperature_c = float(data["temperature_c"])
        humidity_pct = float(data["humidity_pct"])
    except (KeyError, TypeError, ValueError):
        return None, error_response("INVALID_ENVIRONMENT", "temperature_c và humidity_pct phải là số", 400)

    if not -40 <= temperature_c <= 80:
        return None, error_response("TEMPERATURE_OUT_OF_RANGE", "temperature_c phải trong khoảng -40 đến 80°C", 422)
    if not 0 <= humidity_pct <= 100:
        return None, error_response("HUMIDITY_OUT_OF_RANGE", "humidity_pct phải trong khoảng 0 đến 100%", 422)

    try:
        measured_at = parse_measurement_time(data.get("measured_at"))
    except (TypeError, ValueError):
        return None, error_response("INVALID_MEASURED_AT", "measured_at phải là ISO-8601 có timezone", 400)

    return {
        "device_id": device_id.strip(),
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "measured_at": measured_at,
    }, None


def environment_to_dict(reading, alarm):
    result = {
        "id": reading.id,
        "device_id": reading.device_id,
        "temperature_c": reading.temperature_c,
        "humidity_pct": reading.humidity_pct,
        "measured_at": _iso_timestamp(reading.measured_at),
        "received_at": _iso_timestamp(reading.received_at),
        "alarm": dict(alarm),
    }
    result["alarm"]["bpm_measured_at"] = _iso_timestamp(alarm["bpm_measured_at"])
    return result


def validate_measurement(data):
    if not isinstance(data, dict):
        return None, error_response("INVALID_REQUEST", "Body JSON không hợp lệ", 400)

    try:
        bpm = float(data["bpm"])
    except (KeyError, TypeError, ValueError):
        return None, error_response("INVALID_MEASUREMENT", "bpm phải là số", 400)
    if not 0 < bpm <= 120:
        return None, error_response("BPM_OUT_OF_RANGE", "bpm phải lớn hơn 0 và không quá 120", 422)

    source = data.get("source")
    if source not in {"webcam", "esp32cam", "camera_ai"}:
        return None, error_response("INVALID_SOURCE", "source không hợp lệ", 400)

    try:
        measured_at = parse_measurement_time(data.get("measured_at"))
    except (TypeError, ValueError):
        return None, error_response("INVALID_MEASURED_AT", "measured_at phải là ISO-8601 có timezone", 400)

    quality = data.get("quality")
    if quality not in {"valid", "uncertain"}:
        return None, error_response("INVALID_QUALITY", "quality phải là valid hoặc uncertain", 422)

    try:
        quality_score = float(data.get("quality_score"))
    except (TypeError, ValueError):
        return None, error_response("INVALID_QUALITY_SCORE", "quality_score phải là số từ 0 đến 1", 400)
    if not 0 <= quality_score <= 1:
        return None, error_response("INVALID_QUALITY_SCORE", "quality_score phải là số từ 0 đến 1", 422)

    anomaly = data.get("anomaly", "unknown")
    if anomaly not in {"normal", "anomaly", "unknown"}:
        return None, error_response("INVALID_ANOMALY", "anomaly không hợp lệ", 400)
    anomaly_score = data.get("anomaly_score")
    if anomaly_score is not None:
        try:
            anomaly_score = float(anomaly_score)
        except (TypeError, ValueError):
            return None, error_response("INVALID_ANOMALY_SCORE", "anomaly_score phải là số hoặc null", 400)
    anomaly_reason = data.get("anomaly_reason")
    if anomaly_reason is not None and not isinstance(anomaly_reason, str):
        return None, error_response("INVALID_ANOMALY_REASON", "anomaly_reason phải là chuỗi hoặc null", 400)

    features = data.get("features") or {}
    if not isinstance(features, dict):
        return None, error_response("INVALID_FEATURES", "features phải là object", 400)
    normalized_features = {}
    for name in ("fps", "amplitude", "regularity"):
        value = features.get(name)
        if value is None:
            normalized_features[name] = None
            continue
        try:
            normalized_features[name] = float(value)
        except (TypeError, ValueError):
            return None, error_response("INVALID_FEATURES", f"features.{name} phải là số hoặc null", 422)

    return {
        "bpm": bpm,
        "source": source,
        "measured_at": measured_at,
        "quality": quality,
        "quality_score": quality_score,
        "quality_reason": data.get("quality_reason"),
        "anomaly": anomaly,
        "anomaly_score": anomaly_score,
        "anomaly_reason": anomaly_reason,
        "features": normalized_features,
    }, None


@app.route("/")
@caregiver_required
def dashboard():
    return render_template("index.html")


@app.route("/api/latest", methods=["GET"])
@caregiver_required
def get_latest():

    db = SessionLocal()

    try:
        record = (
            db.query(BreathingRecord)
            .order_by(desc(BreathingRecord.created_at))
            .first()
        )

        if record is None:
            return error_response("NO_MEASUREMENT", "Chưa có dữ liệu đo", 404)

        return jsonify(record_to_dict(record)), 200

    finally:
        db.close()


@app.route("/api/history", methods=["GET"])
@caregiver_required
def get_history():
    raw_limit = request.args.get("limit", "100")
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return error_response("INVALID_LIMIT", "limit phải là số nguyên từ 1 đến 1000", 400)
    if not 1 <= limit <= 1000:
        return error_response("INVALID_LIMIT", "limit phải là số nguyên từ 1 đến 1000", 400)

    source = request.args.get("source", "all")
    if source not in {"all", "webcam", "esp32cam", "camera_ai"}:
        return error_response("INVALID_SOURCE", "source không hợp lệ", 400)

    db = SessionLocal()

    try:
        query = (
            db.query(BreathingRecord)
            .order_by(desc(BreathingRecord.created_at))
        )
        if source != "all":
            query = query.filter(BreathingRecord.source == source)
        records = query.limit(limit).all()

        return jsonify({
            "items": [record_to_dict(r) for r in records],
            "limit": limit,
        }), 200

    finally:
        db.close()


@app.route("/api/measurements", methods=["POST"])
@worker_required
def ingest_measurement():
    data, validation_error = validate_measurement(request.get_json(silent=True))
    if validation_error:
        return validation_error

    db = SessionLocal()
    try:
        duplicate = (
            db.query(BreathingRecord)
            .filter(BreathingRecord.measured_at == data["measured_at"])
            .first()
        )
        if duplicate:
            return error_response("DUPLICATE_MEASUREMENT", "Đã tồn tại measurement cùng measured_at", 409)

        features = data["features"]
        record = BreathingRecord(
            bpm=data["bpm"],
            source=data["source"],
            measured_at=data["measured_at"],
            quality=data["quality"],
            quality_score=data["quality_score"],
            quality_reason=data["quality_reason"],
            anomaly=data["anomaly"],
            anomaly_score=data["anomaly_score"],
            anomaly_reason=data["anomaly_reason"],
            feature_fps=features["fps"],
            feature_amplitude=features["amplitude"],
            feature_regularity=features["regularity"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        try:
            process_measurement(db, record)
        except Exception as exc:
            db.rollback()
            print(f"[Alarm] Không xử lý được alert: {exc}")
        return jsonify(record_to_dict(record)), 201
    except Exception:
        db.rollback()
        return error_response("DATABASE_UNAVAILABLE", "Không thể lưu measurement", 503)
    finally:
        db.close()


@app.route("/api/alerts", methods=["GET"])
@caregiver_required
def get_alerts():
    raw_limit = request.args.get("limit", "100")
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return error_response("INVALID_LIMIT", "limit phải là số nguyên từ 1 đến 1000", 400)
    if not 1 <= limit <= 1000:
        return error_response("INVALID_LIMIT", "limit phải là số nguyên từ 1 đến 1000", 400)

    db = SessionLocal()
    try:
        alerts = (
            db.query(Alert)
            .order_by(desc(Alert.created_at))
            .limit(limit)
            .all()
        )
        return jsonify({"items": [alert_to_dict(alert) for alert in alerts]}), 200
    finally:
        db.close()


@app.route("/api/settings/thresholds", methods=["GET"])
@caregiver_required
def get_thresholds():
    db = SessionLocal()
    try:
        return jsonify(threshold_settings_to_dict(get_threshold_settings(db))), 200
    finally:
        db.close()


@app.route("/api/settings/thresholds", methods=["PUT"])
@caregiver_required
def update_thresholds():
    data = request.get_json(silent=True) or {}
    try:
        low = float(data["low"])
        high = float(data["high"])
        temperature_high_c = float(data.get("temperature_high_c", ALERT_TEMPERATURE_HIGH_C))
        consecutive_required = int(data["consecutive_required"])
        cooldown_seconds = int(data["cooldown_seconds"])
    except (KeyError, TypeError, ValueError):
        return error_response("INVALID_THRESHOLDS", "Thiếu hoặc sai kiểu dữ liệu ngưỡng", 400)

    if (
        not 0 < low < high <= 120
        or not 10 <= temperature_high_c <= 50
        or not 1 <= consecutive_required <= 5
        or cooldown_seconds < 60
    ):
        return error_response("INVALID_THRESHOLDS", "Ngưỡng hoặc cooldown ngoài phạm vi hỗ trợ", 422)

    db = SessionLocal()
    try:
        settings = get_threshold_settings(db)
        settings.low = low
        settings.high = high
        settings.temperature_high_c = temperature_high_c
        settings.consecutive_required = consecutive_required
        settings.cooldown_seconds = cooldown_seconds
        settings.updated_at = datetime.now()
        db.commit()
        db.refresh(settings)
        return jsonify(threshold_settings_to_dict(settings)), 200
    finally:
        db.close()


@app.route("/api/environment/readings", methods=["POST"])
@device_required
def ingest_environment_reading():
    data, validation_error = validate_environment(request.get_json(silent=True))
    if validation_error:
        return validation_error

    db = SessionLocal()
    try:
        duplicate = (
            db.query(EnvironmentReading)
            .filter(
                EnvironmentReading.device_id == data["device_id"],
                EnvironmentReading.measured_at == data["measured_at"],
            )
            .first()
        )
        if duplicate:
            return error_response("DUPLICATE_ENVIRONMENT_READING", "Đã tồn tại lần đọc cùng measured_at", 409)

        reading = EnvironmentReading(**data)
        db.add(reading)
        db.commit()
        db.refresh(reading)
        alarm = environment_alarm_decision(db, reading.temperature_c)
        return jsonify(environment_to_dict(reading, alarm)), 201
    except Exception:
        db.rollback()
        return error_response("DATABASE_UNAVAILABLE", "Không thể lưu dữ liệu môi trường", 503)
    finally:
        db.close()


@app.route("/api/environment/latest", methods=["GET"])
@caregiver_required
def get_latest_environment():
    db = SessionLocal()
    try:
        reading = (
            db.query(EnvironmentReading)
            .order_by(desc(EnvironmentReading.received_at))
            .first()
        )
        if reading is None:
            return error_response("NO_ENVIRONMENT_READING", "Chưa có dữ liệu DHT22", 404)
        alarm = environment_alarm_decision(db, reading.temperature_c)
        return jsonify(environment_to_dict(reading, alarm)), 200
    finally:
        db.close()


@app.route("/api/breathing", methods=["POST"])
@caregiver_required
def ingest_breathing():

    data = request.get_json(silent=True)

    if not data or "bpm" not in data:
        return jsonify({"error": "Thiếu field bpm"}), 400

    try:
        bpm_value = float(data["bpm"])

    except (TypeError, ValueError):
        return jsonify({"error": "bpm phải là số"}), 400

    image_path = data.get("image")

    db = SessionLocal()

    try:

        record = BreathingRecord(
            bpm=bpm_value,
            source=data.get("source", "camera_ai"),
            note=data.get("note"),
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        print("=" * 60)
        print(f"[Backend] Nhận dữ liệu : {datetime.now():%Y-%m-%d %H:%M:%S}")
        print(f"[Backend] BPM          : {bpm_value:.2f}")
        print(f"[Backend] Image        : {data.get('image')}")
        print("=" * 60)
        try:
            process_measurement(db, record, image_path=image_path)
        except Exception as exc:
            db.rollback()
            print(f"[Alarm] Không xử lý được alert: {exc}")

        return jsonify(record_to_dict(record)), 201

    finally:
        db.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
    )
