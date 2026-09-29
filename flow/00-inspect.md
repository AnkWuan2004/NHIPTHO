# Stage 00-inspect — Brownfield assessment (existing codebase)

Run this BEFORE planning when the project ALREADY EXISTS. Goal: an honest current-state map so
planning starts from reality, not a blank page. Fill every section from EVIDENCE (read the code),
then check the gate. `/flow assess` seeds the auto-scan and validates this gate.

## Gate — check ALL before planning
- [x] I detected the stack / build / test / run commands (from real files; listed below)
- [x] I mapped the main components/modules and entry points
- [x] I assessed current functionality state (works / partial / broken) with file evidence
- [x] I assessed UI/UX state vs the product's stated goals (or noted "no UI")
- [x] I listed the top risks / tech-debt / known issues
- [x] I noted the test + quality baseline (what is covered vs not)
- [x] A human reviewed this assessment (brownfield assessment is operator-gated)
- [x] Every material claim in this assessment is tagged in the Evidence ledger (no Unknown/Decision-required silently treated as product law)
- [x] No FILL placeholders remain in this file

## Detected (auto-scan)
- Stack: Python 3.12 virtual environment; Flask 3.1.3; SQLAlchemy 2.0.51; OpenCV 4.13; Ultralytics 8.4.75; NumPy/SciPy/Matplotlib; PyTorch CPU build. Sources: `requirements.txt`, `.venv` package inventory.
- Install: `.venv/bin/pip install -r requirements.txt` (documented in `README.md`; the file is UTF-16LE and needs encoding normalization before reliable tooling use).
- Run: `python backend/init_db.py`; `python backend/app.py`; `python ai_worker/breathing_worker.py --camera 0` or `python ai_worker/breathing_worker.py --espcam http://<ESP32-IP>/stream`. Sources: `README.md`, `backend/init_db.py`, `backend/app.py`, `ai_worker/breathing_worker.py`.
- Tests: `tests/*.py` are interactive camera scripts; no automated test runner/configuration or CI workflow was found. Sources: `tests/*.py`, `requirements.txt`.
- Context: `README.md`, `DESIGN.md`, `RETRO.md`, `flow/00-inspect.md`; no `pyproject.toml`, `Dockerfile`, or CI workflow found.

## Ranked surfaces (auto-scan — read these first)
The auto-scan ranks source files by how widely their symbols are referenced (highest-leverage
code first). Start your functionality + risk assessment from the top of that list — the surfaces
most of the codebase depends on are where a hidden cross-cutting risk (e.g. unscoped data access)
is most likely to hide. Inspected: `dashboard/static/js/dashboard.js` (polling, stale status, chart and statistics); `backend/app.py` (three API routes, database writes, alert call); `ai_worker/ai/signal_filter.py` and `breathing_rate.py` (time-aware filtering and peak counting); `backend/models.py` (single breathing record model); `motion_tracker.py`, `breathing_worker.py`, and `roi_extractor.py` (optical flow, ROI, camera/ESP32-CAM loop); `email_sender.py` and `alarm_manager.py` (email alert path). The existing `ultrasonic_worker.py` is present but explicitly excluded from accepted v1 scope by the operator.

## What this product is (from docs/specs/code, not guesses)
This is a local graduation-project web system that estimates the breathing rate of one person lying straight, using either a laptop/USB camera or an AI Thinker ESP32-CAM stream. A caregiver is the intended operator: they sign in, view the latest rate and history, and receive email when the technical threshold or anomaly detector flags an abnormal measurement. The system is an engineering monitoring aid for a controlled demo, not an established medical diagnostic device. (Observed implementation plus operator decisions.)

## Current functionality state (evidence)
- Camera ingestion: **partial**. Laptop/USB camera and MJPEG ESP32-CAM paths exist, including reconnect attempts for ESP32-CAM (`ai_worker/breathing_worker.py:85-120, 186-241`), but physical hardware has not been tested end-to-end.
- Pose/chest ROI: **partial**. YOLO pose keypoints derive a chest ROI and the ROI is periodically smoothed (`ai_worker/breathing_worker.py:130-142, 259-286`, `ai_worker/ai/roi_extractor.py:6-35`). Person selection and keypoint-confidence/occlusion rejection are not robustly specified.
- Motion signal/BPM: **partial**. Optical flow, timestamp-aware resampling, band-pass filtering, prominence-based peak detection, and a 60-second block are implemented (`ai_worker/ai/motion_tracker.py:24-89`, `ai_worker/ai/signal_filter.py:31-87`, `ai_worker/ai/breathing_rate.py:36-77`, `ai_worker/breathing_worker.py:310-375`). Local records include 2.0 and 4.02 BPM outliers, so quality gating and validation remain necessary.
- Backend ingest/history: **works locally, with gaps**. Flask serves `/`, `/api/latest`, `/api/history`, and `/api/breathing`, and SQLAlchemy persists records (`backend/app.py:23-136`, `backend/models.py:13-46`). Authentication, strict schema validation, pagination contract, and health endpoint are missing.
- Dashboard: **partial**. It shows latest BPM, source, freshness, summary statistics, and a line chart (`dashboard/templates/index.html:11-72`, `dashboard/static/js/dashboard.js:1-226`). Login, alert history, configurable thresholds, source comparison, and explicit data-quality state are missing.
- Email alert: **partial**. SMTP email with optional inline image is implemented and gated by `BREATHING_ALERTS_ENABLED` (`backend/alarm_manager.py:1-61`, `backend/email_sender.py:1-85`). It uses process-global cooldown state and lacks persistent alert records, retry policy, and a tested configuration flow.
- Login: **missing**. No auth/session/user model or login UI exists.
- Isolation Forest anomaly detection: **missing**. No scikit-learn dependency, feature pipeline, model persistence, warm-up policy, or anomaly API exists.
- Ultrasonic sensor: **out of scope**. `ai_worker/ultrasonic_worker.py` expects ESP8266 + HC-SR04 over HTTP, but the operator explicitly removed it from v1.

## UI / UX state vs product goals
Present: one Vietnamese dashboard page with current BPM, source, update time, online/offline status, average/min/max, and a recent-history line chart (`dashboard/templates/index.html`, `dashboard/static/js/dashboard.js`). It is a prototype but does not yet support the caregiver workflow: no login gate, no clear abnormal/anomaly explanation, no alert history, no threshold configuration, no camera-mode comparison, and no setup/status screen. The UI should remain local and simple because the operator selected a one-caregiver local deployment.

## Risks / tech-debt / known issues
- P0 — no hardware validation: firmware uses hard-coded Wi-Fi credentials and AI Thinker pin mapping; `/ping` and `/stream` have not been tested on the physical board (`esp32cam_stream.ino:24-26, 28-43, 192-217`; operator report).
- P0 — measurement quality risk: records include implausibly low BPM values, while thresholds differ between worker (`<5/>25`), dashboard (`<10/>30`), and config (`10`) (`ai_worker/breathing_worker.py:150-152`, `backend/alarm_manager.py:6-8`, `dashboard/static/js/dashboard.js:31-36, 54-55`, `backend/config.py:10`).
- P0 — no authentication despite caregiver access requirement: all API routes are unauthenticated (`backend/app.py:23-136`).
- P1 — alert reliability: email state is in memory, only one alert cycle is allowed until a normal reading resets it, and SMTP failures are only printed (`backend/alarm_manager.py:9-61`, `backend/email_sender.py:71-85`).
- P1 — test gap: current tests open a real camera and GUI instead of asserting deterministic behavior (`tests/test_keypoint.py:1-42`, `tests/test_pose.py:1-26`, `tests/test_roi.py:1-195`).
- P1 — reproducibility/docs drift: README says MySQL and references a stale worker filename, while runtime defaults to SQLite and the actual worker is `breathing_worker.py` (`README.md:80-154`, `backend/database.py:7-18`).
- P2 — maintainability: generated caches, captures, database, IDE files, mixed line endings, and uncommitted changes are present; cleanup is permitted by the operator but must be scoped and recoverable.

## Test + quality baseline
Covered informally: live camera/YOLO/ROI experiments in `tests/test_keypoint.py`, `tests/test_pose.py`, and `tests/test_roi.py`; no deterministic assertions or coverage report. Backend smoke checks can be performed by starting `backend/app.py` and calling the API, but no checked-in automated API test exists. The local SQLite database has one `breathing_records` table and 14 records as observed during assessment. The new baseline should add deterministic unit tests for ROI, filtering, BPM, anomaly features, auth, threshold decisions, and API validation, plus a manual hardware acceptance checklist for ESP32-CAM.

## Evidence ledger (claims)

Tag every material claim from Functionality / Risks / Verdict. Do **not** write product
policy as fact unless **Authoritative**. Tags:

| Tag | Meaning |
|-----|---------|
| **Authoritative** | Instruction, accepted decision, product contract, documented procedure |
| **Observed** | Code/config/tests show current behavior |
| **Derived** | Direct operational consequence of observed implementation |
| **Decision required** | Normative/product choice with no authority yet |
| **Unknown** | Repo does not establish the answer |

| Claim | Tag | Source (path or "none") |
|-------|-----|-------------------------|
| Claim | Tag | Source |
| The project is a Python/Flask/SQLAlchemy/AI-worker web system with a browser dashboard. | Observed | `requirements.txt`; `backend/app.py`; `dashboard/templates/index.html` |
| The intended v1 user is one caregiver monitoring one person lying straight on a local network. | Authoritative | Operator answers in this session |
| Both laptop/USB camera and ESP32-CAM must remain supported. | Authoritative | Operator answers; `ai_worker/breathing_worker.py:40-54` |
| Ultrasonic sensing is excluded from v1. | Authoritative | Operator answer; existing `ai_worker/ultrasonic_worker.py` |
| Login is required but exact account lifecycle is not yet specified. | Authoritative / Decision required | Operator answer; no current auth implementation |
| Existing BPM output contains low outliers requiring quality validation. | Observed / Derived | `breathing_monitor.db`; `ai_worker/ai/breathing_rate.py`; `ai_worker/breathing_worker.py` |
| Hardware end-to-end status is unknown because physical ESP32-CAM testing has not occurred. | Unknown / Observed | Operator answer; `esp32cam_stream.ino` |
| Current email alert path is implemented but not validated in this session. | Observed / Unknown | `backend/alarm_manager.py`; `backend/email_sender.py`; operator answer |
| Isolation Forest is an additional anomaly detector, not the sole threshold rule. | Authoritative | Operator answer |

## Verdict
The codebase is healthy enough to build on as a controlled local prototype, but not yet as a completed graduation demo. Fix first: (1) validate ESP32-CAM firmware/stream and camera fallback; (2) establish one threshold and data-quality contract; (3) add local caregiver authentication; (4) harden ROI/person/keypoint confidence and reject unusable signal blocks; (5) add Isolation Forest only after collecting enough baseline data; (6) replace interactive scripts with deterministic tests; and (7) update the local runbook and produce end-to-end evidence. Do not build ultrasonic sensing in this cycle. The operator must review this assessment before the brownfield gate is considered passed.

<!-- auto-scan -->
stack:
  - python (pyproject/requirements)
context files present:
  - README.md
  - tests
ranked surfaces (most-referenced first - inspect these before planning):
  1. dashboard/static/js/dashboard.js  (score 74; canvas, records, setStatus)
  2. backend/app.py  (score 16; dashboard, record_to_dict, get_latest)
  3. ai_worker/ai/signal_filter.py  (score 12; SignalFilter, smooth, _bandpass)
  4. ai_worker/ultrasonic_worker.py  (score 11; status, update_plot, setup_plot)
  5. ai_worker/ai/breathing_rate.py  (score 10; BreathingRateEstimator, estimate)
  6. backend/models.py  (score 8; BreathingRecord)
  7. ai_worker/ai/motion_tracker.py  (score 4; MotionTracker, draw_particles, reset)
  8. ai_worker/breathing_worker.py  (score 4; detect_chest_roi, reopen_espcam, smooth_roi)
  9. ai_worker/ai/roi_extractor.py  (score 3; ROIExtractor, get_chest_roi)
  10. backend/email_sender.py  (score 2; send_breathing_alert)
