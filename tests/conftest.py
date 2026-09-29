import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
AI_DIR = PROJECT_ROOT / "ai_worker"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))


@pytest.fixture
def api_client(monkeypatch, tmp_path):
    module_names = (
        "app",
        "database",
        "models",
        "config",
        "auth",
        "alarm_manager",
        "email_sender",
    )
    for name in module_names:
        sys.modules.pop(name, None)

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'contract.sqlite'}")
    monkeypatch.setenv("CAREGIVER_USERNAME", "caregiver")
    monkeypatch.setenv("CAREGIVER_PASSWORD", "demo-password")
    monkeypatch.setenv("BREATHING_WORKER_TOKEN", "test-worker-token")
    monkeypatch.setenv("BREATHING_ALERTS_ENABLED", "0")

    import app

    return app.app.test_client()
