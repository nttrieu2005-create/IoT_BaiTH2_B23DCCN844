#include <WiFi.h>
#include <PubSubClient.h>
#include <DHTesp.h>
#include <time.h>
#include <sys/time.h>
#include <math.h>

// Broker cong khai chi dung cho du lieu gia lap trong bai thuc hanh.
const char* WIFI_SSID = "Wokwi-GUEST";
const char* MQTT_HOST = "test.mosquitto.org";
const int MQTT_PORT = 1883;
const char* TOPIC = "ptit/iot/b23dccn844/bai2/telemetry";
const char* DEVICE_ID = "B23DCCN844";

const int DHT_PIN = 15, TRIG_PIN = 5, ECHO_PIN = 18, LED_PIN = 2;
const unsigned long SEND_MS = 5000;
WiFiClient wifi;
PubSubClient mqtt(wifi);
DHTesp dht;
unsigned long lastSend = 0, sequenceNo = 0;
char bootId[12];

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, "", 6);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println(" connected");
}

void syncClock() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  Serial.print("NTP");
  for (int i = 0; i < 20 && time(nullptr) < 1700000000; i++) {
    delay(500); Serial.print(".");
  }
  Serial.println(time(nullptr) >= 1700000000 ? " synced" : " unavailable; retry later");
}

void connectMQTT() {
  while (!mqtt.connected()) {
    String id = String("bai2-") + DEVICE_ID + "-" + bootId;
    if (mqtt.connect(id.c_str())) Serial.println("MQTT connected");
    else { Serial.printf("MQTT rc=%d, retry 2s\n", mqtt.state()); delay(2000); }
  }
}

float distanceCm() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long us = pulseIn(ECHO_PIN, HIGH, 30000);
  return us ? us * 0.0343f / 2.0f : NAN;
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  dht.setup(DHT_PIN, DHTesp::DHT22);
  snprintf(bootId, sizeof(bootId), "%08lx", (unsigned long)esp_random());
  connectWiFi(); syncClock();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(384);
}

void loop() {
  connectWiFi();
  if (time(nullptr) < 1700000000) syncClock();
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();
  unsigned long now = millis();
  if (now - lastSend < SEND_MS) return;
  lastSend = now;
  if (time(nullptr) < 1700000000) return; // Can dong ho UTC de do do tre.

  TempAndHumidity v = dht.getTempAndHumidity();
  float cm = distanceCm();
  if (!isfinite(v.temperature) || !isfinite(v.humidity) || !isfinite(cm)) {
    Serial.println("Sensor invalid; skip"); return;
  }
  struct timeval tv;
  gettimeofday(&tv, nullptr);
  unsigned long long sentMs = (unsigned long long)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
  unsigned long seq = ++sequenceNo;
  char payload[384];
  int n = snprintf(payload, sizeof(payload),
    "{\"device_id\":\"%s\",\"boot_id\":\"%s\",\"sequence\":%lu,"
    "\"sent_at_ms\":%llu,\"temperature\":%.2f,\"humidity\":%.2f,"
    "\"distance_cm\":%.2f,\"rssi\":%d,\"uptime_s\":%lu}",
    DEVICE_ID, bootId, seq, sentMs, v.temperature, v.humidity, cm,
    WiFi.RSSI(), millis() / 1000UL);
  if (n < 0 || n >= (int)sizeof(payload)) { Serial.println("JSON too large"); return; }
  bool ok = mqtt.publish(TOPIC, payload); // PubSubClient publish: QoS 0.
  Serial.printf("seq=%lu publish=%s %s\n", seq, ok ? "OK" : "FAILED", payload);
  if (ok) { digitalWrite(LED_PIN, HIGH); delay(80); digitalWrite(LED_PIN, LOW); }
}
