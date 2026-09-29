import os

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "1").lower() in {"1", "true", "yes", "on"}
SMTP_TIMEOUT = float(os.getenv("SMTP_TIMEOUT", "10"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
SECRET_KEY = os.getenv("BREATHING_SECRET_KEY", "dev-only-change-me")
CAREGIVER_USERNAME = os.getenv("CAREGIVER_USERNAME", "caregiver")
CAREGIVER_PASSWORD = os.getenv("CAREGIVER_PASSWORD", "")

ALERT_LOW_THRESHOLD = float(os.getenv("ALERT_LOW_THRESHOLD", "5"))
ALERT_HIGH_THRESHOLD = float(os.getenv("ALERT_HIGH_THRESHOLD", "25"))
ALERT_TEMPERATURE_HIGH_C = float(os.getenv("ALERT_TEMPERATURE_HIGH_C", "30"))
ALERT_CONSECUTIVE_REQUIRED = int(os.getenv("ALERT_CONSECUTIVE_REQUIRED", "1"))
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))
ALERTS_ENABLED = os.getenv("BREATHING_ALERTS_ENABLED", "0").lower() in {
    "1", "true", "yes", "on"
}
BREATHING_THRESHOLD = 10
BPM_FRESHNESS_SECONDS = int(os.getenv("BPM_FRESHNESS_SECONDS", "120"))
BREATHING_DEVICE_TOKEN = os.getenv("BREATHING_DEVICE_TOKEN", "local-device-token")
CAPTURE_FOLDER = "../captures"
