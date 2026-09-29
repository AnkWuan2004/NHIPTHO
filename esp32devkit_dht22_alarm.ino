/**
 * ESP32-S3 DevKit + DHT22 + speaker + warning LED
 *
 * Luong du lieu:
 *   DHT22 -> POST /api/environment/readings -> AlarmDecision -> coi/den
 *
 * Cai thu vien Arduino IDE:
 *   - DHT sensor library by Adafruit
 *   - Adafruit Unified Sensor
 *
 * Dau noi mac dinh:
 *   DHT22 DATA -> GPIO 38 (them dien tro 10K keo len 3.3V neu module khong co)
 *   Speaker    -> GPIO 36
 *   LED canh bao -> GPIO 35 qua dien tro han dong
 *   GND        -> GND, VCC DHT22 -> 3.3V
 */

#include <Arduino.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <time.h>

const char* WIFI_SSID = "TEN_WIFI_CUA_BAN";
const char* WIFI_PASSWORD = "MAT_KHAU_WIFI";
const char* API_URL = "http://192.168.1.100:5000/api/environment/readings";
const char* DEVICE_TOKEN = "local-device-token";
const char* DEVICE_ID = "esp32s3-devkit-01";

constexpr uint8_t DHT_PIN = 38;
constexpr uint8_t SPEAKER_PIN = 36;
constexpr uint8_t WARNING_LED_PIN = 35;
constexpr uint32_t SAMPLE_INTERVAL_MS = 2000;
constexpr float DEFAULT_TEMPERATURE_HIGH_C = 30.0f;

DHT dht(DHT_PIN, DHT22);
float lastTemperatureThresholdC = DEFAULT_TEMPERATURE_HIGH_C;
uint32_t lastSampleMs = 0;

void setAlarm(bool active) {
  digitalWrite(SPEAKER_PIN, active ? HIGH : LOW);
  digitalWrite(WARNING_LED_PIN, active ? HIGH : LOW);
}

bool localTemperatureAlarm(float temperatureC) {
  return !isnan(temperatureC) && temperatureC > lastTemperatureThresholdC;
}

String isoTimestamp() {
  struct tm timeInfo;
  if (!getLocalTime(&timeInfo, 1000)) {
    return "";
  }

  char buffer[32];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(buffer);
}

bool responseBool(const String& body, const char* key) {
  String needle = String("\"") + key + "\":true";
  return body.indexOf(needle) >= 0;
}

float responseNumber(const String& body, const char* key, float fallback) {
  String needle = String("\"") + key + "\":";
  int start = body.indexOf(needle);
  if (start < 0) return fallback;
  start += needle.length();
  int end = start;
  while (end < body.length()) {
    char c = body[end];
    if ((c >= '0' && c <= '9') || c == '.' || c == '-') {
      end++;
    } else {
      break;
    }
  }
  String value = body.substring(start, end);
  if (value.length() == 0) return fallback;
  return value.toFloat();
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Dang ket noi WiFi");
  for (int attempt = 0; attempt < 30 && WiFi.status() != WL_CONNECTED; attempt++) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK, IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi khong san sang; van giu bao dong nhiet do cuc bo");
  }
}

void postEnvironment(float temperatureC, float humidityPct) {
  bool localAlarm = localTemperatureAlarm(temperatureC);
  setAlarm(localAlarm);

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  String measuredAt = isoTimestamp();
  if (measuredAt.length() == 0) {
    Serial.println("Chua dong bo thoi gian NTP; bo qua POST");
    return;
  }

  HTTPClient http;
  if (!http.begin(API_URL)) {
    Serial.println("Khong mo duoc API URL");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", String("Bearer ") + DEVICE_TOKEN);
  String body = String("{\"device_id\":\"") + DEVICE_ID
    + "\",\"temperature_c\":" + String(temperatureC, 2)
    + ",\"humidity_pct\":" + String(humidityPct, 2)
    + ",\"measured_at\":\"" + measuredAt + "\"}";

  int status = http.POST(body);
  String response = http.getString();
  http.end();

  if (status != 201) {
    Serial.printf("API tra HTTP %d; chi dung bao dong nhiet do cuc bo\n", status);
    return;
  }

  float returnedThreshold = responseNumber(
    response, "temperature_high_c", lastTemperatureThresholdC
  );
  if (returnedThreshold >= 10.0f && returnedThreshold <= 50.0f) {
    lastTemperatureThresholdC = returnedThreshold;
  }

  bool backendAlarm = responseBool(response, "buzzer");
  setAlarm(localTemperatureAlarm(temperatureC) || backendAlarm);
  Serial.printf(
    "DHT22: %.1f C, %.1f %%, alarm=%s\n",
    temperatureC,
    humidityPct,
    (localTemperatureAlarm(temperatureC) || backendAlarm) ? "ON" : "OFF"
  );
}

void setup() {
  Serial.begin(115200);
  pinMode(SPEAKER_PIN, OUTPUT);
  pinMode(WARNING_LED_PIN, OUTPUT);
  setAlarm(false);

  dht.begin();
  connectWifi();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void loop() {
  if (millis() - lastSampleMs < SAMPLE_INTERVAL_MS) {
    delay(20);
    return;
  }
  lastSampleMs = millis();

  connectWifi();
  float humidityPct = dht.readHumidity();
  float temperatureC = dht.readTemperature();
  if (isnan(humidityPct) || isnan(temperatureC)) {
    setAlarm(false);
    Serial.println("Khong doc duoc DHT22; kiem tra day DATA/VCC/GND");
    return;
  }

  postEnvironment(temperatureC, humidityPct);
}
