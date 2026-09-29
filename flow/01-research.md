# Stage 01 — Research (inspect first)

Rule: INSPECT what already exists. Evidence required — links, quotes, screenshots.
"I think there's nothing like this" without searching = gate fail.

> Project type (`/flow project-type`, default `web`): items 2 and 4 below are written for a
> **web / market-facing product**. For an **internal tool / cli / library / skill** (no public
> market), use the non-web framing in each item — it is still real evidence (first-party
> friction, who-benefits), NOT an excuse to skip. The semantic gate refuses a market product
> that hides behind the soft framing.

## Gate — check ALL before `/flow next`
- [x] I actually OPENED 3 existing tools/competitors (links below, with one honest note each)
- [x] **(web)** I found 3 REAL user complaints online, quoted, with source links — **OR (non-web/internal)** I named the concrete first-party friction / observed pain that justifies this
- [x] I wrote what competitors CHARGE (real prices) and who pays — **OR (non-web)** what people spend AROUND this problem today (time, a worse tool, manual work)
- [x] **(web)** I named the ONE channel my first 10 users come from (a place, not "social media") — **OR (non-web/internal)** I named who benefits and how they hear about it (release notes / team), and noted "no market channel" is NOT a kill signal for an internal tool
- [x] I wrote why those users would pick this over the status quo (one honest paragraph)
- [x] I wrote what is technically free vs hard for this idea
- [x] No FILL placeholders remain in this file

## What exists already (3 — open them, don't guess)

1. [Nanit Smart Baby Monitor](https://www.nanit.com/) — camera-first breathing-motion monitoring with optional breathing wear and remote notifications; it is polished but designed around infant/crib workflows, account/cloud assumptions, and paid hardware/insight tiers rather than a local adult-caregiver prototype.
2. [Owlet Dream Sock](https://owletcare.com/products/owlet-dream-sock?bvstate=pg%3A3%2Fct%3Ar) — wearable pulse/oxygen monitoring with a base-station/app notification model and historical trends; it offers a different sensing modality and is infant-specific, so it is not a direct low-cost camera substitute.
3. [Withings Sleep Analyzer](https://www.withings.com/en-uk/products/sleep-analyzer) — under-mattress pneumatic sensing for respiratory rate, body movement, and sleep metrics; it avoids cameras but needs a dedicated mattress sensor and is positioned as a commercial sleep product.

## What users say (web: 3 real complaints quoted+linked · non-web: real first-party friction)

1. > “If you get a false alarm on the breathing monitor, it will scare the living shit out of you.” — user comparing Nanit/Owlet, [Reddit discussion](https://www.reddit.com/r/babyrooms/comments/1t10our/nanit_vs_owlet_finishing_up_the_nursery_and_stuck/).
2. > “The Nanit shows as ‘measuring…’ or will send us a note saying ‘Baby not breathing…’” — reported false-event behavior, [Reddit discussion](https://www.reddit.com/r/Nanit/comments/1b8lvwj/absolute_nightmare/).
3. > “The Owlet gave a lot more false alarms” and the user could not tell why from the app — [Reddit discussion](https://www.reddit.com/r/NewParents/comments/1qo2vz4/nanitowlet_false_alarms_how_did_you_react_after/).

## GTM & business reality

Building is the cheap part now. Distribution and willingness-to-pay are where ideas die —
research them BEFORE planning, not after shipping.

### Who pays today, and how much (pricing reference points)

- Nanit Smart Baby Monitor System → from **$289.99**, with optional Insights plans; paid by the caregiver/family. [Nanit pricing page](https://www.nanit.com/).
- Owlet Dream Sock → **$239.99 sale / $299.99 regular** on the US product page; paid by the caregiver/family. [Owlet product page](https://owletcare.com/products/owlet-dream-sock?bvstate=pg%3A3%2Fct%3Ar).
- Withings Sleep Analyzer → **€129.95** launch price in the official press release; paid by the household. [Withings press release](https://media.withings.com/press/press-releases/sleep-analyzer/sleep-analyzer_pr_en.pdf).
- Status quo for this graduation prototype → free existing webcam/laptop plus caregiver time spent checking manually; the cost is missed observations and no continuous local history, not a subscription.

### The first-10-users channel (web) · who-benefits (non-web/internal)

This is a controlled graduation-project prototype rather than a paid market launch. The first 10 evaluators will come from the Group 12 project team, classmates/lecturers at the department demonstration, and caregivers known to the team; they will be invited directly through the **Zalo group of Group 12's graduation project** and the local demonstration session. There is no public market channel or payment test in this cycle; the benefit is a real end-to-end evaluation with named caregiver participants.

### Why switch (vs the status quo)

The named evaluators would choose this prototype for the graduation demonstration because it is local, uses hardware the team controls, keeps the camera pipeline and history on the local machine, supports both laptop camera and ESP32-CAM, and exposes the signal-quality/anomaly reason instead of only emitting a black-box alarm. It does not beat commercial devices on certification, polish, or clinical validation; its honest switch reason is low-cost experimentation, local control, and inspectable AI behavior for one controlled caregiver scenario.

## Technically free vs hard

- Free (solved by libraries/platforms): Flask, SQLAlchemy, SQLite, OpenCV, Ultralytics YOLO pose, NumPy/SciPy filtering, Chart.js, local session UI, and ESP32 HTTP streaming primitives.
- Hard (custom work, real risk): reliable chest ROI/person/keypoint selection, separating breathing motion from body/camera motion, ESP32-CAM Wi-Fi/FPS stability, calibration and signal-quality rejection, threshold consistency, Isolation Forest warm-up/features, secure password/session handling, email reliability, and producing hardware-backed evidence in one week.
