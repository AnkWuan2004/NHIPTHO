# Stage 05 — Interface Contract (the seam)

The contract is whatever sits between your core and its consumer. For a web app that's
API endpoints (the table below). For a CLI it's commands + flags + output shapes; for a
plugin it's hooks + filters; for a pipeline it's input/output file schemas. Keep the
table's SPIRIT — every feature maps to an interface, every interface has its shapes
written before code — and adapt the columns to your project's shape.

Written BEFORE any code. Backend cards build TO this table; UI cards consume FROM it.
The #1 AI-build failure is producer/consumer drift — backend ships one shape, UI assumes
another, both look green. This file is the cheap fix.

## Gate — check ALL before `/flow next`
- [x] Every PRD feature maps to at least one INTERFACE below (web: endpoint · cli: command · library: public function · skill: command/file)
- [x] Every interface has its INPUT and OUTPUT shapes written (web: request+response · cli: flags+output/exit code · library: args+return)
- [x] Access/effects column filled for every interface (web: public/token/admin · non-web: writes/side-effects, or "none")
- [x] No FILL placeholders remain in this file
- [x] No unresolved open decisions (resolve via /flow clarify, or assume/cut)
- [x] Every write interface names the failure shape (status or exit + body), not only the happy path
- [x] Every interface that can return empty names the empty shape (empty list / 404 / exit 2), or an explicit `none`
- [x] Access/effects is a concrete token (web: public/token/admin · non-web: writes/side-effects or "none") — not a vibe word (secure, authenticated, restricted)

## OpenAPI / Swagger rule  (web only — N/A for cli/library/skill)

For non-web types there is no served spec; the equivalent "no producer/consumer drift" check
is the per-type done-evidence (the command runs / the API imports / the skill installs+runs).
For `web`:

This table is the PLANNING source of truth. If the framework serves a spec (FastAPI →
`/openapi.json` + `/docs`), the served spec is the RUNTIME artifact of this same contract:
- Path/method/shapes here and in the served spec must agree — the contract-test card
  asserts every endpoint in this table exists in the live `/openapi.json` with matching
  request/response shapes.
- Change flows ONE way: amend this file first, then the code, then the spec follows.
- **Docs land with the API, not after**: the served spec is live from the vertical-slice
  card onward, and every backend card's verify checks its endpoints appear in the live
  `/docs` with correct schemas. The contract-test card later asserts full agreement —
  but by then the docs have been growing card by card, never a catch-up task.
- Keep `/docs` enabled at least until v1 ships — it's the free human-readable contract.

## Interfaces  (web: endpoints · cli: commands · library: functions · skill: commands)

Adapt the columns to your project type. Web: Method/Path/Access(=auth: public/token/admin)/
Request/Response. CLI: Command/Flags/Access(=side-effects)/Input/Output+exit. Library:
Function/—/Access(=none)/Args/Return. The shared column below is "Access/Effects".

| Method/Interface | Path/Name | Access/Effects | Input shape | Output shape |
|---|---|---|---|---|
| GET | `/healthz` | public; none | none | `200 {"status":"ok","version":string,"database":"ok"|"error"}`; `503 Error` when DB unavailable; never returns measurement data |
| GET | `/login` | public; none | none | `200` Vietnamese login HTML; empty/error: `500 Error` |
| POST | `/api/auth/login` | public; creates caregiver session | `{ "username": string, "password": string }` | `200 {"authenticated":true,"user":{"username":string}}`; `400 Error` malformed; `401 Error` wrong credentials; `429 Error` after rate limit |
| POST | `/api/auth/logout` | token(caregiver); clears session | none | `200 {"authenticated":false}`; `401 Error` when no session |
| GET | `/api/me` | token(caregiver); none | none | `200 {"authenticated":true,"user":{"username":string}}`; `401 Error` when absent/expired |
| GET | `/` | public; redirects to login or serves dashboard | none | `302 /login` when no caregiver session; `200` dashboard HTML when token(caregiver); `500 Error` template failure |
| GET | `/api/latest` | token(caregiver); none | none | `200 Measurement`; `404 {"error":"NO_MEASUREMENT","message":string}` when empty; `401 Error` |
| GET | `/api/history?limit=100&source=all` | token(caregiver); none | `limit`: integer 1–1000; `source`: `all|webcam|esp32cam|camera_ai` | `200 {"items":Measurement[],"limit":int}`; empty shape `{"items":[],"limit":int}`; `400 Error` invalid query; `401 Error` |
| POST | `/api/measurements` | token(worker); writes measurement and may create alert | `{ "bpm": number, "source": "webcam"|"esp32cam"|"camera_ai", "measured_at": ISO-8601, "quality": "valid"|"uncertain", "quality_score": number 0..1, "quality_reason": string|null, "anomaly": "normal"|"anomaly"|"unknown", "anomaly_score": number|null, "anomaly_reason": string|null, "features": {"fps":number|null,"amplitude":number|null,"regularity":number|null} }` | `201 Measurement` for valid/uncertain record; `400 Error` malformed; `401 Error` bad worker token; `409 Error` duplicate timestamp; `422 Error` `quality=invalid`, out-of-range BPM, or feature inconsistency; `503 Error` DB unavailable |
| GET | `/api/alerts?limit=100` | token(caregiver); none | `limit`: integer 1–1000 | `200 {"items":Alert[]}`; empty shape `{"items":[]}`; `400 Error`; `401 Error` |
| GET | `/api/settings/thresholds` | token(caregiver); none | none | `200 ThresholdSettings`; `401 Error` |
| PUT | `/api/settings/thresholds` | token(caregiver); updates local setting | `{ "low": number, "high": number, "temperature_high_c": number (10..50), "consecutive_required": integer 1–5, "cooldown_seconds": integer >=60 }` | `200 ThresholdSettings`; `400 Error` malformed; `401 Error`; `422 Error` when low >= high, temperature is outside 10..50°C, or another value is invalid |
| POST | `/api/environment/readings` | token(device); writes DHT22 reading and evaluates local alarm decision | `{ "device_id": string, "temperature_c": number (-40..80), "humidity_pct": number (0..100), "measured_at": ISO-8601 }` | `201 EnvironmentReading` with `alarm`; `400 Error` malformed; `401 Error` bad device token; `409 Error` duplicate timestamp; `422 Error` sensor value out of range; `503 Error` DB unavailable |
| GET | `/api/environment/latest` | token(caregiver); none | none | `200 EnvironmentReading`; `404 {"error":"NO_ENVIRONMENT_READING","message":string}` when empty; `401 Error` |

## Shared shapes (objects used by multiple interfaces)

```
Error {
  error: string,              // stable uppercase code
  message: string,            // Vietnamese human-readable message
  details: object|null
}

Measurement {
  id: integer,
  bpm: number,
  source: "webcam"|"esp32cam"|"camera_ai",
  measured_at: string,        // ISO-8601 local/UTC with explicit timezone
  quality: "valid"|"uncertain"|"invalid",
  quality_score: number|null, // 0..1
  quality_reason: string|null,
  anomaly: "normal"|"anomaly"|"unknown",
  anomaly_score: number|null,
  anomaly_reason: string|null,
  features: { fps:number|null, amplitude:number|null, regularity:number|null },
  alert_id: integer|null
}

Alert {
  id: integer,
  measurement_id: integer,
  kind: "threshold"|"anomaly"|"combined",
  status: "created"|"email_sent"|"email_failed",
  bpm: number,
  message: string,
  created_at: string,
  email_sent_at: string|null
}

ThresholdSettings {
  low: number,                // default 5
  high: number,               // default 25
  temperature_high_c: number, // default 30
  consecutive_required: integer,
  cooldown_seconds: integer
}

EnvironmentReading {
  id: integer,
  device_id: string,
  temperature_c: number,
  humidity_pct: number,
  measured_at: string,        // ISO-8601 local/UTC with explicit timezone
  received_at: string,
  alarm: AlarmDecision
}

AlarmDecision {
  active: boolean,
  reasons: ("temperature_high"|"breathing_low"|"breathing_high")[],
  severity: "none"|"warning"|"critical", // none=normal; warning=temperature only; critical=any breathing reason
  buzzer: boolean,
  led: "off"|"red",
  temperature_high_c: number,
  bpm: number|null,
  bpm_measured_at: string|null,
  bpm_stale: boolean,
  message: string
}
```

## Feature → interface map

Reference each PRD feature by its `FRn` id so the mapping is machine-checkable
(`/flow consistency` flags any `FRn` with no interface here).

- `FR1` → `GET /healthz`, `GET /api/latest`, `GET /api/history?source=...`.
- `FR2` → `POST /api/measurements`, `GET /api/latest`, `GET /api/history`.
- `FR3` → `GET /login`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/me`, protected `GET /`.
- `FR4` → `GET /api/latest`, `GET /api/history`, `GET /api/alerts`.
- `FR5` → `GET/PUT /api/settings/thresholds`, `POST /api/measurements`, `GET /api/alerts`.
- `FR6` → `POST /api/measurements`, `GET /api/latest`, `GET /api/history`, `GET /api/alerts`.
- `FR7` → contract-test suite covering every endpoint above; its observable interface is the JSON/status contract and the failure shapes.
- `FR8` → `GET /healthz` plus the runbook commands that initialize DB, start backend/worker, and call the protected API after login.
- `FR9` → `POST /api/environment/readings`, `GET /api/environment/latest`, and `GET/PUT /api/settings/thresholds`.

## Open decisions

Record unresolved product choices here (add a line like `- [ ] which tenant key?`). Do not invent auth, tenancy, retention, or billing to clear FILL. Resolve via /flow clarify, or assume/cut.

None — auth, storage, local deployment, camera sources, threshold authority, anomaly fallback, ESP32 DevKit request/response alarm path, and ultrasonic exclusion are locked in the approved ADR/PRD.
