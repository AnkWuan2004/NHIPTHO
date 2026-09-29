from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime
)

from sqlalchemy.orm import declarative_base

from datetime import datetime

Base = declarative_base()


class BreathingRecord(Base):
    __tablename__ = "breathing_records"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    bpm = Column(
        Float,
        nullable=False
    )

    source = Column(
        String(50),
        default="camera_ai"
    )

    note = Column(
        String(255),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.now
    )

    measured_at = Column(DateTime, nullable=True, index=True)
    quality = Column(String(20), nullable=True)
    quality_score = Column(Float, nullable=True)
    quality_reason = Column(String(255), nullable=True)
    anomaly = Column(String(20), nullable=True)
    anomaly_score = Column(Float, nullable=True)
    anomaly_reason = Column(String(255), nullable=True)
    feature_fps = Column(Float, nullable=True)
    feature_amplitude = Column(Float, nullable=True)
    feature_regularity = Column(Float, nullable=True)
    alert_id = Column(Integer, nullable=True)


class CaregiverAccount(Base):
    __tablename__ = "caregiver_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class EnvironmentReading(Base):
    __tablename__ = "environment_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), nullable=False, index=True)
    temperature_c = Column(Float, nullable=False)
    humidity_pct = Column(Float, nullable=False)
    measured_at = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=datetime.now, nullable=False, index=True)


class ThresholdSettings(Base):
    __tablename__ = "threshold_settings"

    id = Column(Integer, primary_key=True, default=1)
    low = Column(Float, nullable=False, default=5.0)
    high = Column(Float, nullable=False, default=25.0)
    temperature_high_c = Column(Float, nullable=False, default=30.0)
    consecutive_required = Column(Integer, nullable=False, default=1)
    cooldown_seconds = Column(Integer, nullable=False, default=300)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    measurement_id = Column(Integer, nullable=False)
    kind = Column(String(20), nullable=False, default="threshold")
    status = Column(String(20), nullable=False, default="created")
    bpm = Column(Float, nullable=False)
    message = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_error = Column(String(255), nullable=True)
