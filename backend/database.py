import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'breathing_monitor.db')}",
)

if not DATABASE_URL.startswith("sqlite:"):
    raise RuntimeError(
        "Dự án này chỉ dùng SQLite. DATABASE_URL phải có dạng sqlite:///đường_dẫn.db"
    )

connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)


def ensure_schema():
    """Create new tables and add measurement columns to the prototype DB.

    The project already has local SQLite databases created by the prototype.
    SQLAlchemy's create_all() does not alter an existing table, so the small
    additive migration below keeps those databases usable without destructive
    resets. The column names are fixed internal identifiers, not user input.
    """
    from models import Base

    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("breathing_records")}
    additions = {
        "measured_at": "DATETIME",
        "quality": "VARCHAR(20)",
        "quality_score": "FLOAT",
        "quality_reason": "VARCHAR(255)",
        "anomaly": "VARCHAR(20)",
        "anomaly_score": "FLOAT",
        "anomaly_reason": "VARCHAR(255)",
        "feature_fps": "FLOAT",
        "feature_amplitude": "FLOAT",
        "feature_regularity": "FLOAT",
        "alert_id": "INTEGER",
    }

    missing = [(name, sql_type) for name, sql_type in additions.items() if name not in existing]
    if missing:
        with engine.begin() as connection:
            for name, sql_type in missing:
                connection.execute(text(
                    f"ALTER TABLE breathing_records ADD COLUMN {name} {sql_type}"
                ))

    threshold_existing = {
        column["name"] for column in inspect(engine).get_columns("threshold_settings")
    }
    if "temperature_high_c" not in threshold_existing:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE threshold_settings ADD COLUMN temperature_high_c FLOAT NOT NULL DEFAULT 30.0"
            ))
