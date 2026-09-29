from datetime import datetime, timedelta, timezone

from sqlalchemy import desc

from config import (
    ALERTS_ENABLED,
    ALERT_CONSECUTIVE_REQUIRED,
    ALERT_COOLDOWN_SECONDS,
    ALERT_HIGH_THRESHOLD,
    ALERT_LOW_THRESHOLD,
    ALERT_TEMPERATURE_HIGH_C,
    BPM_FRESHNESS_SECONDS,
)
from email_sender import send_breathing_alert
from models import Alert, BreathingRecord, ThresholdSettings


def get_threshold_settings(db):
    settings = db.query(ThresholdSettings).filter_by(id=1).first()
    if settings is None:
        settings = ThresholdSettings(
            id=1,
            low=ALERT_LOW_THRESHOLD,
            high=ALERT_HIGH_THRESHOLD,
            temperature_high_c=ALERT_TEMPERATURE_HIGH_C,
            consecutive_required=ALERT_CONSECUTIVE_REQUIRED,
            cooldown_seconds=ALERT_COOLDOWN_SECONDS,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def threshold_settings_to_dict(settings):
    return {
        "low": float(settings.low),
        "high": float(settings.high),
        "temperature_high_c": float(settings.temperature_high_c),
        "consecutive_required": int(settings.consecutive_required),
        "cooldown_seconds": int(settings.cooldown_seconds),
    }


def is_abnormal(bpm, settings):
    return bpm < settings.low or bpm > settings.high


def environment_alarm_decision(db, temperature_c):
    """Combine the DHT22 reading with a recent, usable BPM measurement."""
    settings = get_threshold_settings(db)
    latest = (
        db.query(BreathingRecord)
        .filter(BreathingRecord.measured_at.isnot(None))
        .order_by(desc(BreathingRecord.measured_at), desc(BreathingRecord.created_at))
        .first()
    )

    reasons = []
    if temperature_c > settings.temperature_high_c:
        reasons.append("temperature_high")

    bpm_measured_at = None
    bpm_stale = True
    bpm_value = None
    if latest is not None:
        bpm_value = float(latest.bpm)
        bpm_measured_at = latest.measured_at or latest.created_at
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        age_seconds = (now_utc - bpm_measured_at).total_seconds()
        bpm_stale = (
            age_seconds < 0
            or age_seconds > BPM_FRESHNESS_SECONDS
            or latest.quality not in {"valid", "uncertain"}
        )
        if not bpm_stale:
            if latest.bpm < settings.low:
                reasons.append("breathing_low")
            elif latest.bpm > settings.high:
                reasons.append("breathing_high")

    active = bool(reasons)
    breathing_alert = any(reason.startswith("breathing_") for reason in reasons)
    if breathing_alert:
        severity = "critical"
    elif active:
        severity = "warning"
    else:
        severity = "none"

    messages = []
    if "temperature_high" in reasons:
        messages.append(
            f"Nhiệt độ {temperature_c:.1f}°C vượt ngưỡng {settings.temperature_high_c:.1f}°C"
        )
    if "breathing_low" in reasons:
        messages.append(f"Nhịp thở {bpm_value:.1f} lần/phút thấp hơn ngưỡng")
    if "breathing_high" in reasons:
        messages.append(f"Nhịp thở {bpm_value:.1f} lần/phút cao hơn ngưỡng")
    if not messages:
        messages.append("Không có cảnh báo hiện tại")

    return {
        "active": active,
        "reasons": reasons,
        "severity": severity,
        "buzzer": active,
        "led": "red" if active else "off",
        "temperature_high_c": float(settings.temperature_high_c),
        "bpm": bpm_value,
        "bpm_measured_at": bpm_measured_at,
        "bpm_stale": bpm_stale,
        "message": "; ".join(messages),
    }


def _consecutive_abnormal_count(db, measurement, settings):
    records = (
        db.query(BreathingRecord)
        .order_by(desc(BreathingRecord.created_at))
        .limit(settings.consecutive_required)
        .all()
    )
    count = 0
    for record in records:
        if is_abnormal(record.bpm, settings):
            count += 1
        else:
            break
    return count


def _cooldown_alert(db, settings):
    since = datetime.now() - timedelta(seconds=settings.cooldown_seconds)
    return (
        db.query(Alert)
        .filter(Alert.kind == "threshold", Alert.created_at >= since)
        .order_by(desc(Alert.created_at))
        .first()
    )


def process_measurement(db, measurement, image_path=None):
    """Create one threshold alert per cooldown window.

    Measurement persistence happens before this function is called. Email
    delivery is best-effort: SMTP failure changes the alert status but never
    rolls back the measurement.
    """
    settings = get_threshold_settings(db)
    if not is_abnormal(measurement.bpm, settings):
        return None

    consecutive = _consecutive_abnormal_count(db, measurement, settings)
    if consecutive < settings.consecutive_required:
        print(
            f"[Alarm] Chưa đủ số lần bất thường liên tiếp: "
            f"{consecutive}/{settings.consecutive_required}"
        )
        return None

    existing = _cooldown_alert(db, settings)
    if existing is not None:
        measurement.alert_id = existing.id
        db.commit()
        print(
            f"[Alarm] Bỏ qua alert trùng trong cooldown {settings.cooldown_seconds}s "
            f"(alert_id={existing.id})"
        )
        return existing

    message = (
        f"Nhịp thở {measurement.bpm:.1f} BPM vượt ngưỡng "
        f"{settings.low:.1f}–{settings.high:.1f} BPM"
    )
    alert = Alert(
        measurement_id=measurement.id,
        kind="threshold",
        status="created",
        bpm=measurement.bpm,
        message=message,
    )
    db.add(alert)
    db.flush()
    measurement.alert_id = alert.id

    if not ALERTS_ENABLED:
        print("[Alarm] Alert đã lưu; email đang tắt")
        db.commit()
        db.refresh(alert)
        return alert

    try:
        send_breathing_alert(bpm=measurement.bpm, image_path=image_path)
        alert.status = "email_sent"
        alert.email_sent_at = datetime.now()
        print(f"[Alarm] Email alert đã gửi (alert_id={alert.id})")
    except Exception as exc:
        alert.status = "email_failed"
        alert.email_error = str(exc)[:255]
        print(f"[Alarm] SMTP thất bại (alert_id={alert.id}): {exc}")

    db.commit()
    db.refresh(alert)
    return alert


def process(bpm, image_path=None):
    """Compatibility wrapper for the pre-contract caller."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        measurement = BreathingRecord(
            bpm=bpm,
            source="camera_ai",
            quality="uncertain",
            quality_reason="legacy alarm path",
            anomaly="unknown",
        )
        db.add(measurement)
        db.commit()
        db.refresh(measurement)
        return process_measurement(db, measurement, image_path=image_path)
    finally:
        db.close()
