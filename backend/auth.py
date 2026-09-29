from functools import wraps
from time import monotonic

from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import CAREGIVER_PASSWORD, CAREGIVER_USERNAME
from models import CaregiverAccount


MAX_LOGIN_ATTEMPTS = 5
RATE_WINDOW_SECONDS = 60
_failed_attempts = {}


def ensure_caregiver_account(db):
    """Provision the single local caregiver account when a password is supplied."""
    account = db.query(CaregiverAccount).filter_by(username=CAREGIVER_USERNAME).first()
    if account or not CAREGIVER_PASSWORD:
        return account

    account = CaregiverAccount(
        username=CAREGIVER_USERNAME,
        password_hash=generate_password_hash(CAREGIVER_PASSWORD),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def _client_key():
    return request.remote_addr or "unknown"


def _is_rate_limited():
    now = monotonic()
    attempts = [
        timestamp
        for timestamp in _failed_attempts.get(_client_key(), [])
        if now - timestamp < RATE_WINDOW_SECONDS
    ]
    _failed_attempts[_client_key()] = attempts
    return len(attempts) >= MAX_LOGIN_ATTEMPTS


def _record_failed_attempt():
    _failed_attempts.setdefault(_client_key(), []).append(monotonic())


def authenticate(db, username, password):
    if _is_rate_limited():
        return None, "rate_limited"

    account = ensure_caregiver_account(db)
    if (
        account is None
        or username != account.username
        or not isinstance(password, str)
        or not check_password_hash(account.password_hash, password)
    ):
        _record_failed_attempt()
        return None, "invalid_credentials"

    _failed_attempts.pop(_client_key(), None)
    return account, None


def login_user(account):
    session.clear()
    session["caregiver_authenticated"] = True
    session["caregiver_id"] = account.id
    session["caregiver_username"] = account.username


def logout_user():
    session.clear()


def caregiver_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("caregiver_authenticated") is True:
            return view(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({
                "error": "AUTH_REQUIRED",
                "message": "Cần đăng nhập caregiver",
            }), 401
        return redirect(url_for("login", next=request.path))

    return wrapped
