# Stage 04 — ADR (architecture decisions)

Short. The most valuable section is what you are NOT doing and why.

## Gate — check ALL before `/flow next`
- [x] Each decision has a one-line "why" and a one-line "what I rejected"
- [x] The NOT-doing list is written
- [x] Decisions cover: data storage, auth approach, deploy target
- [x] No FILL placeholders remain in this file

## Decisions

| # | Decision | Why | Rejected alternative |
|---|---|---|---|
| 1 | SQLite là database duy nhất qua SQLAlchemy | Vì v1 chạy một máy local, cần zero-setup và dễ backup file; model ORM hiện có sẵn | MySQL server bắt buộc hoặc cloud database vì tăng điểm lỗi cài đặt và không phục vụ demo một người |
| 2 | Một tài khoản caregiver local, session cookie, password hash bằng thư viện chuẩn của Werkzeug; không tự đăng ký | Đủ yêu cầu bảo vệ dashboard/API và phù hợp một người dùng; không tạo hệ thống identity lớn | OAuth/Google login, nhiều role, multi-tenant và reset password vì không cần cho local v1 và tăng bề mặt bảo mật |
| 3 | Chạy Flask + worker trên laptop Windows trong mạng local; webcam là fallback bắt buộc, ESP32-CAM là input thứ hai | Phù hợp điều kiện demo, không cần cloud credential/public DNS và giữ được camera pipeline hiện tại | Public hosting/Docker/cloud/mobile app vì không có thời gian threat model, network setup và live deployment |
| 4 | REST/JSON contract trước code, tách auth/measurement/alert; response có `quality`, `anomaly`, `source`, timestamp và failure shape | Ngăn backend/UI tự suy diễn shape; dashboard và worker cùng dùng một vocabulary | Gửi payload tự do theo từng worker hoặc để UI đọc trực tiếp database vì đã gây drift ngưỡng/source trong prototype |
| 5 | Giữ pipeline YOLO pose → chest ROI → optical-flow signal → filter/peaks; thêm quality gate và Isolation Forest trên feature đã tính | Tận dụng code và model sẵn có, có thể kiểm thử deterministic; Isolation Forest là lớp advisory có warm-up | Tự huấn luyện YOLO/deep model mới hoặc Isolation Forest realtime nhiều tầng vì thiếu dữ liệu và vượt một tuần |
| 6 | Threshold `<5`/`>25` là cảnh báo chính; Isolation Forest chỉ bổ sung `anomaly/unknown` và không được suppress threshold | Threshold có hành vi giải thích được và không phụ thuộc model chưa đủ baseline; anomaly detector xử lý tín hiệu bất thường | Dùng duy nhất model anomaly hoặc gửi email cho mọi anomaly chưa xác nhận vì dễ báo giả và mất niềm tin |
| 7 | Không xây cảm biến siêu âm trong v1; giữ file cũ ngoài contract/card mới | Operator đã loại tính năng, và camera-only làm scope có thể kiểm chứng trong 1 tuần | Tích hợp ESP8266 + HC-SR04 song song vì chưa test phần cứng và không thuộc core acceptance |
| 8 | ESP32 DevKit V1 đọc DHT22 mỗi 2 giây và POST `/api/environment/readings`; backend trả quyết định cảnh báo kết hợp nhiệt độ với BPM còn mới, firmware điều khiển còi/đèn theo phản hồi | Một request/response đủ cho một node local, dễ fixture-test và không cần broker; backend giữ một nguồn quyết định để dashboard/email/thiết bị không lệch ngưỡng | MQTT/WebSocket, cloud IoT hoặc để ESP32 tự đọc database vì tăng vận hành và tạo nhiều nguồn sự thật |
| 9 | Ngưỡng nhiệt độ cao mặc định là 30°C, lưu cùng `ThresholdSettings` và được gửi lại trong `AlarmDecision`; firmware giữ ngưỡng cuối cùng/default để tiếp tục cảnh báo nhiệt độ khi backend mất kết nối, còn BPM cũ hơn 120 giây không được dùng để bật cảnh báo nhịp thở | Ngưỡng minh bạch, chỉnh được trong local demo, có bảo vệ cục bộ khi mạng lỗi và tránh dùng dữ liệu nhịp thở đã stale để kích còi | Suy luận nhiệt độ y tế hoặc giữ cảnh báo nhịp thở vô thời hạn khi camera/backend mất kết nối |

## NOT doing in v1 (and why it's safe to skip)

- Public Internet, cloud storage, Docker/production deployment, mobile app.
- Multi-user/multi-patient/role admin, registration, password reset, tenancy and billing.
- Ultrasonic sensor, Telegram, continuous video recording, PDF/CSV export and video sharing.
- New model training, clinical calibration, medical-device claims, or automated clinical decisions.
- Background job queue, microservices, realtime WebSocket/MQTT streaming, IoT fleet management, and horizontal scaling.
