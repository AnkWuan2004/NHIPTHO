const POLL_INTERVAL_MS = 5000;
const HISTORY_LIMIT = 100;
// Worker hien gui BPM moi 60s (xem --interval trong breathing_worker.py).
// Nguong nay PHAI lon hon chu ky gui cua worker, neu khong dashboard se
// bao "mat ket noi" mot cach gia tao giua 2 lan gui. Neu ban doi
// --interval sang gia tri khac 60, nho cap nhat lai so nay cho khop
// (vd interval=30 -> dat khoang 45000-50000).
const STALE_AFTER_MS = 90000; // 90s = 60s chu ky + 30s du phong tre mang

const bpmValueEl = document.getElementById("bpm-value");
const lastUpdatedEl = document.getElementById("last-updated");
const lastSourceEl = document.getElementById("last-source");
const lastQualityEl = document.getElementById("last-quality");
const lastAnomalyEl = document.getElementById("last-anomaly");
const lastAnomalyReasonEl = document.getElementById("last-anomaly-reason");
const historyEmptyEl = document.getElementById("history-empty");
const alertListEl = document.getElementById("alert-list");
const alertsEmptyEl = document.getElementById("alerts-empty");
const statusDotEl = document.getElementById("status-dot");
const statusTextEl = document.getElementById("status-text");
const statAvgEl = document.getElementById("stat-avg");
const statMinEl = document.getElementById("stat-min");
const statMaxEl = document.getElementById("stat-max");
const temperatureValueEl = document.getElementById("temperature-value");
const humidityValueEl = document.getElementById("humidity-value");
const environmentStateEl = document.getElementById("environment-state");
const environmentAlarmEl = document.getElementById("environment-alarm");
const environmentAlarmTitleEl = document.getElementById("environment-alarm-title");
const environmentAlarmMessageEl = document.getElementById("environment-alarm-message");
const environmentUpdatedEl = document.getElementById("environment-updated");

let chart = null;

const SOURCE_LABELS = {
  webcam: "Camera máy tính",
  esp32cam: "ESP32-CAM",
  camera_ai: "Camera + AI",
};
const QUALITY_LABELS = {
  valid: "Ổn định",
  uncertain: "Cần kiểm tra",
  invalid: "Không hợp lệ",
};
const ANOMALY_LABELS = {
  normal: "Bình thường",
  anomaly: "Bất thường",
  unknown: "Chưa đủ dữ liệu",
};
const ALARM_REASON_LABELS = {
  temperature_high: "Nhiệt độ cao",
  breathing_low: "Nhịp thở thấp",
  breathing_high: "Nhịp thở cao",
};

function displayLabel(value, labels) {
  return labels[value] || value || "—";
}

function formatTime(isoString) {
  const d = new Date(isoString);
  return d.toLocaleTimeString("vi-VN", { hour12: false });
}

function recordTimestamp(record) {
  return record.measured_at || record.recorded_at || record.created_at;
}

function setStatus(online) {
  statusDotEl.classList.toggle("online", online);
  statusDotEl.classList.toggle("offline", !online);
  statusTextEl.textContent = online ? "Đang giám sát" : "Mất kết nối với cảm biến";
}

function resetEnvironment() {
  temperatureValueEl.textContent = "--";
  humidityValueEl.textContent = "--";
  environmentStateEl.textContent = "Chưa có dữ liệu";
  environmentAlarmEl.dataset.state = "empty";
  environmentAlarmTitleEl.textContent = "Chưa có trạng thái";
  environmentAlarmMessageEl.textContent = "Chưa nhận được dữ liệu từ DHT22.";
  environmentUpdatedEl.textContent = "—";
}

function updateEnvironment(record) {
  if (!record || !record.alarm) {
    resetEnvironment();
    return;
  }

  const alarm = record.alarm;
  const reasons = (alarm.reasons || []).map((reason) => ALARM_REASON_LABELS[reason] || reason);
  temperatureValueEl.textContent = Number(record.temperature_c).toFixed(1);
  humidityValueEl.textContent = Number(record.humidity_pct).toFixed(1);
  environmentStateEl.textContent = alarm.active ? "Đang cảnh báo" : "Bình thường";
  environmentAlarmEl.dataset.state = alarm.active ? "active" : "normal";
  environmentAlarmTitleEl.textContent = alarm.active
    ? (reasons.join(" · ") || "Cần chú ý")
    : "Không có cảnh báo";
  environmentAlarmMessageEl.textContent = alarm.message || "Không có cảnh báo hiện tại";
  environmentUpdatedEl.textContent = `Cập nhật lúc ${formatTime(record.received_at || record.measured_at)}`;
}

function updateLatest(record) {
  if (!record) {
    bpmValueEl.textContent = "--";
    lastUpdatedEl.textContent = "—";
    lastSourceEl.textContent = "—";
    lastQualityEl.textContent = "—";
    lastAnomalyEl.textContent = "—";
    lastAnomalyReasonEl.textContent = "Chưa có đánh giá";
    setStatus(false);
    return;
  }

  const timestamp = recordTimestamp(record);

  bpmValueEl.textContent = Number(record.bpm).toFixed(1);
  lastUpdatedEl.textContent = formatTime(timestamp);
  lastSourceEl.textContent = displayLabel(record.source, SOURCE_LABELS);
  lastQualityEl.textContent = displayLabel(record.quality, QUALITY_LABELS);
  lastAnomalyEl.textContent = displayLabel(record.anomaly, ANOMALY_LABELS);
  lastAnomalyReasonEl.textContent = record.anomaly_reason || "Chưa đủ baseline để phân loại";

  const isAbnormal = record.bpm < 5 || record.bpm > 25;
  bpmValueEl.classList.toggle("warning", isAbnormal);

  const ageMs = Date.now() - new Date(timestamp).getTime();
  setStatus(ageMs <= STALE_AFTER_MS);
}

// Tách riêng try/catch cho updateStats và renderChart -- để nếu 1 trong 2
// bị lỗi thì cái còn lại vẫn chạy được, không "rớt" theo nhau.

function updateStats(records) {
  try {
    if (!records || !records.length) {
      statAvgEl.textContent = "--";
      statMinEl.textContent = "--";
      statMaxEl.textContent = "--";
      return;
    }
    const values = records.map((r) => Number(r.bpm)).filter((v) => !Number.isNaN(v));
    if (!values.length) {
      statAvgEl.textContent = "--";
      statMinEl.textContent = "--";
      statMaxEl.textContent = "--";
      return;
    }
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    statAvgEl.textContent = avg.toFixed(1);
    statMinEl.textContent = Math.min(...values).toFixed(1);
    statMaxEl.textContent = Math.max(...values).toFixed(1);
  } catch (err) {
    console.error("[dashboard] Lỗi khi tính avg/min/max:", err);
  }
}

function renderChart(records) {
  try {
    if (historyEmptyEl) {
      historyEmptyEl.hidden = records.length > 0;
    }
    const ordered = [...records].reverse();
    const labels = ordered.map((r) => formatTime(recordTimestamp(r)));
    const values = ordered.map((r) => Number(r.bpm));

    if (chart) {
      chart.data.labels = labels;
      chart.data.datasets[0].data = values;
      chart.update();
      return;
    }

    const canvas = document.getElementById("history-chart");
    if (!canvas) {
      console.error("[dashboard] Không tìm thấy canvas #history-chart trong DOM");
      return;
    }
    if (typeof Chart === "undefined") {
      console.error("[dashboard] Chart.js chưa được load (kiểm tra mạng/CDN)");
      return;
    }

    const ctx = canvas.getContext("2d");
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "BPM",
            data: values,
            borderColor: "#4F46E5",
            backgroundColor: "rgba(79, 70, 229, 0.12)",
            fill: true,
            tension: 0.35,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHitRadius: 12,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        // "nearest" + intersect:false -> chi can ren chuot GAN diem
        // (khong can trung tuyet doi vao diem an) la tooltip hien ra.
        interaction: {
          mode: "nearest",
          axis: "x",
          intersect: false,
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => `Thời gian: ${items[0]?.label ?? ""}`,
              label: (item) => `BPM: ${Number(item.parsed.y).toFixed(1)} lần/phút`,
            },
          },
          zoom: {
            pan: {
              enabled: true,
              mode: "x",
            },
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: "x",
            },
            limits: {
              x: { minRange: 5 }, // khong cho zoom sau hon 5 diem du lieu
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 6 } },
          y: { grid: { color: "#E4E4E7" }, suggestedMin: 5, suggestedMax: 30 },
        },
      },
    });

    canvas.addEventListener("dblclick", () => {
      if (chart) chart.resetZoom();
    });
  } catch (err) {
    console.error("[dashboard] Lỗi khi vẽ chart lịch sử:", err);
  }
}

async function fetchLatest() {
  try {
    const res = await fetch("/api/latest");
    if (res.status === 404) {
      updateLatest(null);
      return;
    }
    if (res.status === 401) {
      window.location.href = "/login?next=/";
      return;
    }
    if (!res.ok) {
      console.error(`[dashboard] /api/latest trả lỗi HTTP ${res.status}`);
      return;
    }
    const data = await res.json();
    updateLatest(data);
  } catch (err) {
    setStatus(false);
    console.error("[dashboard] Lỗi khi lấy /api/latest:", err);
  }
}

async function fetchHistory() {
  try {
    const res = await fetch(`/api/history?limit=${HISTORY_LIMIT}`);
    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = "/login?next=/";
        return;
      }
      console.error(`[dashboard] /api/history trả lỗi HTTP ${res.status}`);
      return;
    }
    const data = await res.json();
    const records = Array.isArray(data?.items) ? data.items : [];

    // Log này giúp xác định ngay nguyên nhân: nếu thấy số > 0 ở console
    // nhưng chart/stat vẫn trống -> lỗi nằm ở renderChart/updateStats
    // (đã tách try/catch riêng ở trên). Nếu thấy 0 -> chưa có dữ liệu
    // thật trong DB (kiểm tra lại worker / migration DB).
    console.log(`[dashboard] /api/history trả về ${records.length} bản ghi`);

    renderChart(records);
    updateStats(records);
  } catch (err) {
    console.error("[dashboard] Lỗi khi lấy /api/history:", err);
  }
}

function renderAlerts(alerts) {
  if (!alertListEl) return;
  alertListEl.replaceChildren();
  if (alertsEmptyEl) alertsEmptyEl.hidden = alerts.length > 0;

  for (const alert of alerts) {
    const item = document.createElement("li");
    const status = alert.status === "email_sent"
      ? "Đã gửi email"
      : alert.status === "email_failed"
        ? "Gửi email lỗi"
        : "Đã ghi nhận";
    item.textContent = `${formatTime(alert.created_at)} · ${Number(alert.bpm).toFixed(1)} BPM · ${status} · ${alert.message}`;
    alertListEl.appendChild(item);
  }
}

async function fetchAlerts() {
  try {
    const res = await fetch("/api/alerts?limit=10");
    if (res.status === 401) {
      window.location.href = "/login?next=/";
      return;
    }
    if (!res.ok) {
      console.error(`[dashboard] /api/alerts trả lỗi HTTP ${res.status}`);
      return;
    }
    const data = await res.json();
    renderAlerts(Array.isArray(data?.items) ? data.items : []);
  } catch (err) {
    console.error("[dashboard] Lỗi khi lấy /api/alerts:", err);
  }
}

async function fetchEnvironment() {
  try {
    const res = await fetch("/api/environment/latest");
    if (res.status === 404) {
      resetEnvironment();
      return;
    }
    if (res.status === 401) {
      window.location.href = "/login?next=/";
      return;
    }
    if (!res.ok) {
      console.error(`[dashboard] /api/environment/latest trả lỗi HTTP ${res.status}`);
      return;
    }
    updateEnvironment(await res.json());
  } catch (err) {
    resetEnvironment();
    console.error("[dashboard] Lỗi khi lấy dữ liệu DHT22:", err);
  }
}

function poll() {
  fetchLatest();
  fetchHistory();
  fetchAlerts();
  fetchEnvironment();
}

const resetZoomBtn = document.getElementById("reset-zoom-btn");
if (resetZoomBtn) {
  resetZoomBtn.addEventListener("click", () => {
    if (chart) chart.resetZoom();
  });
}

poll();
setInterval(poll, POLL_INTERVAL_MS);
