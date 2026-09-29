# Stage 03 — PRD

1-2 pages max. Test: could a stranger build v1 from this without asking you anything?

## Gate — check ALL before `/flow next`
- [x] Every section below is filled from MY scope decision (stage 02), not re-expanded
- [x] Success metric is a NUMBER, not vibes ("save time" fails; "first response < 2h" passes)
- [x] Each feature names the user action and the observable result, tagged with a stable `FRn:` id
- [x] Pain & gain is a MAPPING TABLE: every pain cites evidence (a stage-01 quote or a named observation), and names the v1 feature that kills it; every v1 feature kills at least one pain
- [x] A stranger could build v1 from this without asking me anything
- [x] No FILL placeholders remain in this file
- [x] No unresolved open decisions (resolve via /flow clarify, or assume/cut)
- [x] No unquantified adjectives (fast / secure / intuitive / robust / prominent) in Features or NFRs — a number, a named constraint, or cut the word
- [x] Every `FRn` names the failure or empty case (what the user sees when it fails or there is nothing), or an explicit `none`

## Context

Người chăm sóc người thân nằm theo dõi tại nhà cần biết diễn biến nhịp thở giữa các lần quan sát thủ công. Các sản phẩm thương mại cho thấy camera, wearable và cảm biến dưới nệm đều có thể cung cấp dữ liệu nhưng thường đi kèm phần cứng chuyên dụng, cloud/subscription hoặc các phản hồi về báo động giả. Đồ án này vào khoảng trống của một prototype local có thể kiểm tra được: dùng webcam hoặc ESP32-CAM, xử lý tại máy tính, lưu lịch sử và giải thích chất lượng tín hiệu. V1 ưu tiên một người được theo dõi, một tài khoản chăm sóc và một kịch bản người nằm thẳng.

## Target users

Ngoài dashboard, một ESP32 DevKit V1 đọc DHT22 và phát cảnh báo cục bộ bằng còi/đèn khi nhiệt độ hoặc nhịp thở vượt ngưỡng.

**Người chăm sóc tại nhà** — người không chuyên kỹ thuật, cần mở dashboard local để xem một người đang nằm theo dõi, kiểm tra giá trị mới nhất và lịch sử, rồi phản ứng khi có cảnh báo email. Họ không cần chỉnh thuật toán; khi tín hiệu không đủ, hệ thống phải nói rõ cần kiểm tra camera/tư thế thay vì hiển thị một con số có vẻ chính xác.

## Pain & gain (mapping table — the traceability spine of the PRD)

Every row: a concrete pain, the evidence it's real, what people do about it today, the
ONE v1 feature that kills it, and the observable gain. If a feature kills no pain, cut
it; if a pain has no feature, it goes to the "not addressed" list — honestly.

| # | Persona | Pain (concrete) | Evidence (stage-01 quote/source or named observation) | Today's workaround | V1 feature that kills it | Observable gain |
|---|---|---|---|---|---|---|
| P1 | Người chăm sóc | Báo động giả gây hoảng sợ và làm mất niềm tin vào monitor | Stage 01 quote về false alarm trên Nanit/Owlet: “it will scare the living shit out of you” | Kiểm tra trực tiếp, dùng thêm thiết bị khác | FR2 + FR6 | Cảnh báo kèm trạng thái chất lượng/tín hiệu và nguồn phát hiện |
| P2 | Người chăm sóc | Không thể quan sát liên tục và không có lịch sử BPM local | Named observation: current project only exposed latest/history prototype after worker POST; manual checking remains the fallback | Đứng cạnh người được theo dõi hoặc ghi chép thủ công | FR1 + FR4 | Có BPM mới nhất, timestamp, lịch sử và trạng thái camera trên một trang |
| P3 | Người chăm sóc | Camera/ROI/movement có thể làm block tín hiệu sai hoặc không đo được | Repo observation: local DB already contains 2.0 and 4.02 BPM outliers; ROI currently takes the first detected person | Bỏ qua số đo hoặc thử lại bằng mắt | FR2 | Block lỗi được gắn `quality=invalid/uncertain` hoặc bỏ qua, không ghi như kết quả chắc chắn |
| P4 | Người chăm sóc | Dữ liệu dashboard/API local hiện chưa yêu cầu đăng nhập | Repo observation: `backend/app.py` exposes `/`, `/api/latest`, `/api/history`, `/api/breathing` without auth | Không mở dashboard từ mạng khác hoặc dựa vào máy local | FR3 | Người chưa đăng nhập nhận 401/redirect và không xem được dữ liệu |
| P5 | Người chăm sóc | Cảnh báo cần đến email và không được gửi lặp vô hạn | Repo observation: SMTP path exists but `mail_sent` is process-global and failures are printed | Tự kiểm tra email hoặc gọi điện thủ công | FR5 | Một bất thường tạo một alert record/email theo cooldown; khi bình thường trở lại trạng thái reset |
| P6 | Nhóm đồ án/người đánh giá | Không thể tái chạy và chứng minh kết quả nếu chỉ có script mở camera | Repo observation: `tests/*.py` open real camera/UI and contain no deterministic assertions | Chạy thủ công trước buổi demo | FR7 + FR8 | Fixture/test/checklist/runbook tái hiện được các luồng chính trong local environment |
| P7 | Người chăm sóc/người ở gần người được theo dõi | Email hoặc dashboard có thể không được nhìn thấy ngay tại nơi đặt thiết bị khi có nhiệt độ cao hoặc nhịp thở bất thường | Named operator request: bổ sung ESP32 DevKit V1, DHT22, còi và đèn để cảnh báo tại chỗ | Kiểm tra thủ công hoặc chờ người chăm sóc xem dashboard | FR9 | Còi/đèn tại chỗ bật theo nguyên nhân cảnh báo; nhiệt độ và trạng thái thiết bị vẫn được lưu để truy vết |

### Pains NOT addressed in v1 (deliberate — tie to the scope cut list)

- Nhiều người dùng/nhiều bệnh nhân → deferred vì v1 có một caregiver và một người theo dõi; v2 cần tenancy/role/data isolation.
- Cloud/mobile/public access → deferred vì operator chọn local; v2 cần deploy/auth/network/threat model riêng.
- Video recording/export/chia sẻ → deferred vì không cần cho core BPM demo và làm tăng rủi ro dữ liệu hình ảnh.
- Cảm biến siêu âm → deferred/removed theo quyết định operator; không có FR hoặc interface trong v1.
- Cảnh báo Internet/MQTT, mobile push và nhiều thiết bị chấp hành → deferred vì v1 chỉ cần một ESP32 DevKit trong mạng local.

## Problem statement

V1 cần biến luồng camera thành một chỉ số nhịp thở có chất lượng được xác định, để một người chăm sóc local có thể xem, truy vết và nhận cảnh báo mà không phụ thuộc vào việc quan sát liên tục. Khi có nhiệt độ cao hoặc nhịp thở bất thường, ESP32 DevKit phải phát cảnh báo cục bộ bằng còi và đèn dựa trên quyết định từ backend. Thành công không phải là hiển thị mọi số BPM, mà là phân biệt được kết quả hợp lệ với tín hiệu không đủ và chứng minh được bằng test + một lần chạy phần cứng/webcam thật.

## Features (user-centric — action → observable result)

Tag each v1 feature with a stable id `FRn:` (functional requirement) — the traceability
anchor. Every `FRn` must later be claimed by a card (`implements: FRn`) and served by an
interface in the contract (`FRn →`); `/flow consistency` checks this mechanically.

- **FR1:** Người chăm sóc chọn webcam hoặc nhập URL ESP32-CAM, bấm bắt đầu đo, và thấy trạng thái nguồn (`connecting`, `measuring`, `stale`, `error`) cùng BPM mới nhất; nếu không mở được nguồn, thấy lỗi có hướng dẫn và webcam vẫn có thể được chọn làm fallback.
- **FR2:** Người chăm sóc xem kết quả BPM theo block 60 giây; hệ thống chọn keypoint/ROI hợp lệ, lọc tín hiệu và trả `valid`, `uncertain` hoặc `invalid` kèm lý do; nếu thiếu frame/keypoint/FPS, dashboard thấy “không đủ dữ liệu” thay vì giá trị 0 giả.
- **FR3:** Người chăm sóc mở `/login`, gửi username/password đã cấu hình local và được chuyển vào dashboard; nếu sai hoặc chưa đăng nhập, `/` và API dữ liệu trả redirect/401 và không trả record.
- **FR4:** Người chăm sóc xem BPM hiện tại, nguồn, thời gian đo, trung bình/thấp nhất/cao nhất, lịch sử và lý do chất lượng trên dashboard; khi chưa có record, thấy empty state và không có chart rỗng gây hiểu nhầm.
- **FR5:** Người chăm sóc cấu hình/khởi tạo ngưỡng kỹ thuật `<5` hoặc `>25`, và khi có bất thường liên tiếp theo policy hệ thống tạo alert record + gửi email một lần trong cooldown; nếu SMTP lỗi, dashboard/log hiển thị `email_failed` nhưng bản ghi đo vẫn được giữ.
- **FR6:** Người chăm sóc xem nhãn `anomaly`/`normal` từ Isolation Forest sau giai đoạn warm-up; mô hình dùng feature BPM/chất lượng/tín hiệu đã định nghĩa, không chặn threshold alert; khi chưa đủ dữ liệu hoặc model lỗi, nhãn là `unknown` và dashboard nói rõ lý do.
- **FR7:** Người phát triển chạy unit/API tests với tín hiệu mô phỏng và fixture camera, rồi chạy checklist webcam/ESP32-CAM; khi test/fixture không có hoặc không đạt, lệnh trả lỗi rõ ràng và không được ghi nhận là verification thành công.
- **FR8:** Người đánh giá làm theo README để cài dependency, tạo DB, chạy backend/worker và mở dashboard local; nếu thiếu biến môi trường/email/model, runbook nêu lỗi và đường fallback, không yêu cầu kiến thức ngầm.
- **FR9:** Người vận hành cấp nguồn cho ESP32 DevKit V1, thiết bị đọc DHT22 theo chu kỳ 2 giây và gửi nhiệt độ/độ ẩm lên backend; backend kết hợp nhiệt độ với BPM hợp lệ còn mới, trả `AlarmDecision`, và ESP32 bật còi cùng đèn đỏ khi nhiệt độ vượt 30°C hoặc BPM thấp hơn 5/cao hơn 25. Nếu backend không sẵn sàng, ESP32 vẫn cảnh báo nhiệt độ cao bằng ngưỡng cục bộ đã biết nhưng tắt phần cảnh báo nhịp thở; nếu cảm biến lỗi hoặc BPM đã cũ, thiết bị hiển thị trạng thái tương ứng và không tạo cảnh báo nhịp thở giả.

## Non-functional requirements

- Local only: backend binds to the local machine/LAN demo; no cloud upload or public deployment is required.
- Auth: all dashboard/data routes require the single local caregiver session; credentials come from environment/setup, are never committed, and passwords are stored only as hashes.
- API latency: p95 for `/api/latest`, `/api/history`, and login response is <=500 ms on the demo laptop with <=1000 records.
- Worker stability: the worker must run for 30 minutes without an unhandled exception; a bad block is skipped with an observable reason.
- Measurement cadence: one non-overlapping 60-second block produces at most one BPM record; no record is created for an invalid block.
- UI: Vietnamese text, responsive layout for a 1366px laptop and a 390px viewport, no emoji, and data-quality state visible beside the BPM.
- Privacy: camera frames are not continuously stored; an alert snapshot may be saved locally only when configured, and its path is never exposed to unauthenticated clients.
- Device safety: the environment endpoint requires a device token; DHT22 readings are sampled every 2 seconds, a BPM result is considered fresh for 120 seconds, and the firmware disables only the breathing-alert portion when the backend response is stale or malformed while retaining local high-temperature protection.

## Tech stack

Backend: Python 3.12 + Flask 3.1 + SQLAlchemy 2.0, modular auth/measurement/alert services. Database: SQLite only through `DATABASE_URL`, with no MySQL compatibility in v1. AI: OpenCV, Ultralytics YOLO pose, NumPy/SciPy, and `scikit-learn` IsolationForest added for v1. Hardware: ESP32 DevKit V1, DHT22, buzzer and red LED using Arduino Wi-Fi/HTTP firmware. Frontend: existing Jinja HTML, vanilla JavaScript, CSS, Chart.js via CDN. Deploy target: local Windows demo machine; commands run from the project virtual environment; webcam fallback and ESP32-CAM are supported camera inputs, while the ESP32 DevKit is the local alarm actuator.

## Success metric (numbers only)

1. **10/10** unauthenticated access checks are blocked from dashboard/data routes.
2. **>=90%** of 20 synthetic/recorded 60-second signal blocks produce either a BPM with a valid/uncertain quality label or an explicit invalid reason; zero silent `0 BPM` results.
3. The worker runs **30 minutes** without an unhandled exception in webcam mode; ESP32-CAM reconnect succeeds in **3/3** forced disconnect trials when hardware is available.
4. A threshold test creates **1 email and 1 alert record within 60 seconds**, then produces no duplicate email during a **5-minute** cooldown.
5. Isolation Forest labels **>=90%** of an offline fixture set containing injected outlier blocks as `anomaly` or `unknown` with no crash; it is not evaluated as a clinical accuracy claim.
6. A fresh setup following the runbook reaches the local dashboard in **<=15 minutes** on the demo laptop.
7. In **3/3** fixture/API trials, a temperature reading above 30°C returns an active `temperature_high` decision, and in **3/3** trials a fresh BPM outside `<5`/`>25` returns the corresponding breathing reason; normal readings return inactive.
8. With a physical ESP32 DevKit and DHT22 available, the device posts **15 consecutive** readings at 2-second cadence and activates/deactivates the buzzer and red LED correctly for temperature and fresh-BPM alert fixtures; if hardware is unavailable, the HTTP fixture proof is recorded without claiming physical proof.

## Open decisions

Record unresolved product choices here (add a line like `- [ ] which tenant key?`). Do not invent auth, tenancy, retention, or billing to clear FILL. Resolve via /flow clarify, or assume/cut.

None — scope decisions are locked for one local caregiver account, one monitored person, two camera modes, technical thresholds (`<5`/`>25` BPM and `>30°C`), advisory Isolation Forest, email, one ESP32 DevKit V1 alarm node, and no ultrasonic sensor.

## Assumptions

Informed defaults (industry-standard or already locked by the operator or an ADR). A bullet that encodes product law (who can access what, tenancy, retention, billing) with no operator/ADR authority is an open decision or a stop, not a silent default.

- The initial caregiver credential is provisioned from environment variables or a setup command; there is no self-registration in v1.
- Threshold alerts are authoritative; anomaly detection adds context and cannot suppress a threshold alert.
- The worker may skip invalid blocks, but it must expose the reason and continue processing later blocks.
- The ESP32-CAM hardware path is verified when available; webcam mode is the required demo fallback.
- The ESP32 DevKit is a single local alarm node; the backend returns the combined decision in response to each DHT22 reading, so no realtime broker is required.
- The temperature alarm has a local firmware fallback using the last known/default 30°C threshold; the breathing alarm is suppressed when no recent BPM result is available.
