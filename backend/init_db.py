from database import engine
from database import SessionLocal
from models import Base
from auth import ensure_caregiver_account
from config import CAREGIVER_PASSWORD, CAREGIVER_USERNAME

Base.metadata.create_all(
    bind=engine
)

print("Database initialized")

db = SessionLocal()
try:
    account = ensure_caregiver_account(db)
    if account:
        print(f"Caregiver account ready: {CAREGIVER_USERNAME}")
    else:
        print("Caregiver account not provisioned: set CAREGIVER_PASSWORD before login")
finally:
    db.close()
