# Stage 02 — Scope (go/no-go)

Scope = features chosen by IMPACT × COST, inside your time budget.
KILL here is cheap and smart. Killing a weak idea at this gate is a SUCCESS outcome.

## Impact rubric (business value — score BEFORE looking at cost)

| Impact | Meaning |
|---|---|
| H | moves money or the core promise: gets users in (acquisition), gets them paying (revenue), or delivers the one job they came for |
| M | keeps users / saves real time weekly (retention, operations) |
| L | nice-to-have; nobody would pay for or switch over it |

Decision matrix: **H-impact features justify B/C cost** (via the C-paths below).
**L-impact features must be grade A or they're cut** — and even grade-A L-features are
cut when the budget is tight. The classic failure is a v1 full of A-grade L-impact
features: cheap to build, worthless to sell.

## AI coding grade rubric

| Grade | Meaning | Examples |
|---|---|---|
| A | cheap for AI | CRUD, forms, dashboards, content sites, API wrappers |
| B | moderate | file processing, 3rd-party integrations, auth via library, single LLM call, HITL AI drafts |
| C | expensive | realtime, payments from scratch, custom auth, autonomous agentic AI pipelines, heavy concurrency |

**Grade is a COST estimate, not a permission.** The gate is fit(grades, budget), not "no C allowed."
When a C feature is the real need, three honest paths:
1. **The C feature IS the product** → invert the cut: C goes FIRST (riskiest assumption first),
   everything else is minimized to serve it, and the budget is renegotiated against reality.
   But: one C proves the value prop — its siblings are v2 cards, not v1 scope.
2. **Re-architect C down to B** (highest-leverage move): multi-step agent → single LLM call;
   auto-send → human-approves-draft; custom pipeline → managed service / library.
   Same user value, one grade cheaper.
3. **Irreducible C that doesn't fit the budget** → KILL or re-budget. Both are honest.

## Gate — check ALL before `/flow next`
- [x] Every feature below has an IMPACT (H/M/L with the business reason) AND a grade (A/B/C)
- [x] No L-impact feature above grade A survives in v1
- [x] The suggested-features section was actually considered (each suggestion has an in/out decision)
- [x] fit(grades, budget) holds — every C in scope is justified as path 1, 2, or 3 above (written next to the feature)
- [x] If the product IS a C feature: it is FIRST in build order, and its sibling C features are on the cut list
- [x] The cut list is written (what I am NOT building in v1)
- [x] GO / KILL decision is written below
- [x] No FILL placeholders remain in this file
- [x] No unresolved open decisions (resolve via /flow clarify, or assume/cut)

## Time budget

1 tuần lịch, 1 người triển khai chính; ưu tiên bản demo local có bằng chứng chạy thật hơn là mở rộng chức năng. Ngày đầu tiên dành cho kiểm tra firmware/stream ESP32-CAM, baseline webcam và đường cảnh báo ESP32 DevKit; nếu phần cứng chưa sẵn sàng thì webcam và fixture HTTP là đường dự phòng để không chặn kiểm thử phần mềm.

## Features in v1 (each with impact AND grade)

- **AI đo nhịp thở và kiểm soát chất lượng tín hiệu** — Impact **H** (lời hứa cốt lõi: người chăm sóc nhận được chỉ số có thể kiểm tra) — Grade **C**, path 1: đây là chính sản phẩm nên phải làm đầu tiên; tối thiểu hóa phạm vi bằng YOLO pose có sẵn, ROI ngực một người nằm thẳng, optical flow/band-pass/peak detection, confidence và trạng thái “không đủ dữ liệu” thay vì tự huấn luyện model mới.
- **Hỗ trợ webcam và ESP32-CAM MJPEG** — Impact **H** (cho phép trình diễn và kiểm thử hai nguồn camera) — Grade **B**, path 2: dùng stream HTTP hiện có, giữ webcam làm fallback, chỉ bổ sung health/reconnect/timeout và cấu hình URL.
- **Đăng nhập một tài khoản người chăm sóc local** — Impact **H** (bảo vệ dashboard và dữ liệu theo yêu cầu người dùng) — Grade **B**, path 2: dùng session cookie + password hash qua thư viện chuẩn, không xây đăng ký/phân quyền nhiều cấp.
- **Dashboard local cho BPM hiện tại, trạng thái, lịch sử và nguồn camera** — Impact **H** (người chăm sóc cần xem kết quả và diễn biến) — Grade **A** (CRUD/chart/UI hiện có, mở rộng có kiểm soát).
- **Một nguồn ngưỡng cảnh báo thống nhất + email** — Impact **H** (biến phát hiện thành hành động cho người chăm sóc) — Grade **B**, path 2: giữ email SMTP hiện có, cấu hình ngưỡng qua config/session, thêm chống gửi lặp và bản ghi cảnh báo; không thêm Telegram trong v1.
- **Isolation Forest phát hiện bất thường bổ sung cho ngưỡng** — Impact **H** (giảm phụ thuộc vào một giá trị BPM và phát hiện block tín hiệu bất thường) — Grade **B**, path 2: dùng một mô hình `sklearn.ensemble.IsolationForest` trên feature đã tính sẵn, warm-up/offline fit và fallback về threshold khi chưa đủ dữ liệu; không huấn luyện realtime phức tạp.
- **Bộ test tự động, dữ liệu mô phỏng và checklist phần cứng** — Impact **M** (giảm rủi ro demo hỏng và cho phép lặp nhanh) — Grade **A** (unit/API tests và fixture tín hiệu tổng hợp).
- **Runbook local và tài liệu bảo vệ** — Impact **M** (giúp người khác cài/chạy lại được) — Grade **A** (chuẩn hóa README/encoding/lệnh chạy, sơ đồ luồng và giới hạn).
- **ESP32 DevKit V1 + DHT22 + còi/đèn cảnh báo** — Impact **H** (đưa cảnh báo nhiệt độ và nhịp thở ra thiết bị tại chỗ để người xung quanh nhận biết) — Grade **B**, path 2: dùng thư viện DHT22 và HTTP request/response; backend giữ vai trò kết hợp tín hiệu, không thêm MQTT/WebSocket hay cloud.

## Suggested features (impact-first — proposed, not decided)

Up to 3 features NOT in the original idea, each chosen for business impact (how does this
get users in / get money in / keep users?). Grounded in the stage-01 GTM findings — e.g.
the first-10-users channel often implies a share/invite/referral surface; the pricing
research often implies an upsell or a paid tier. Default is OUT; each needs an explicit
decision.

- **Hiển thị lý do cảnh báo và chất lượng tín hiệu** — Impact **H** (phản hồi người dùng cho thấy báo động giả làm mất niềm tin; local prototype cần giải thích được) — Grade **A** — **IN**, bắt buộc trong trạng thái đo và lịch sử.
- **Xuất CSV/PDF báo cáo** — Impact **L** (hữu ích khi nộp/báo cáo nhưng không cần cho core monitoring) — Grade **A** — **OUT**, làm sau khi live demo ổn định.
- **Telegram/cloud/public URL/multi-user role** — Impact **M** (mở rộng tiện dụng nhưng không cần cho demo một người local) — Grade **B/C** — **OUT**, cắt để giữ thời gian cho hardware và accuracy.

## Cut list (NOT in v1 — deferred, not deleted)

- Cảm biến siêu âm/ESP8266 + HC-SR04 — đã bị operator loại khỏi v1; không đưa vào card/contract mới.
- Telegram, cloud storage, public deployment, mobile app — không phù hợp local demo một tuần.
- Điều khiển thiết bị từ Internet, MQTT/WebSocket, nhiều board cảnh báo hoặc nhiều người được theo dõi — chưa cần cho prototype local.
- Nhiều người dùng, nhiều bệnh nhân, role admin, reset password, đăng ký tài khoản — vượt mô hình một caregiver.
- Tự huấn luyện YOLO hoặc mô hình deep learning mới — thiếu dữ liệu và không cần để chứng minh pipeline hiện tại.
- Video recording liên tục, replay, chia sẻ ảnh, export PDF/CSV — không thuộc core acceptance.

## Decision

**GO** — phạm vi một tuần đủ để hoàn thiện một vertical slice local có đăng nhập, đo BPM từ hai camera, cảnh báo, anomaly detection bổ sung, test và bằng chứng chạy thật; các phần mở rộng được cắt để bảo vệ độ tin cậy của demo.

## Open decisions

Record unresolved product choices here (add a line like `- [ ] which tenant key?`). Do not invent auth, tenancy, retention, or billing to clear FILL. Resolve via /flow clarify, or assume/cut.

None — operator has selected local deployment, one caregiver account, both camera modes, threshold plus Isolation Forest, ESP32 DevKit V1 + DHT22 + còi/đèn, and no ultrasonic sensing.

## Assumptions

Informed defaults (industry-standard or already locked by the operator or an ADR). A bullet that encodes product law (who can access what, tenancy, retention, billing) with no operator/ADR authority is an open decision or a stop, not a silent default.

- The local system has one caregiver account and one monitored person per session, based on the operator's decision.
- Threshold alerts remain authoritative; Isolation Forest is advisory and must not suppress a threshold alert.
- SQLite is the only v1 local store; MySQL configuration is intentionally out of scope to keep the demo zero-setup.
- A failed ESP32-CAM test does not kill the demo: webcam mode is the documented fallback, while the hardware gap remains visible in evidence.
- DHT22 is sampled every 2 seconds; the technical high-temperature default is 30°C and is configurable with the other local thresholds.
- A breathing alert is evaluated only from a recent BPM record (at most 120 seconds old); if BPM is stale, the device reports the stale state and does not invent a breathing alarm.
