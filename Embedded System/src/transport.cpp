#include "transport.h"

#include <WiFi.h>

#include <string.h>

#include "lantern_config.h"

namespace {
constexpr uint32_t kWifiTimeoutMs = 10000;
constexpr uint32_t kHttpTimeoutMs = 5000;
constexpr size_t kWriteChunkBytes = 512;
const char* kBoundary = "----LanternAudioBoundary";

bool writeBytes(WiFiClient& client, const uint8_t* data, size_t length) {
  size_t offset = 0;
  while (offset < length) {
    const size_t chunk = min(kWriteChunkBytes, length - offset);
    const size_t written = client.write(data + offset, chunk);
    if (written == 0) return false;
    offset += written;
  }
  return true;
}

bool writeString(WiFiClient& client, const String& value) {
  return writeBytes(
      client,
      reinterpret_cast<const uint8_t*>(value.c_str()),
      value.length());
}

void putUint32LE(uint8_t* target, uint32_t value) {
  target[0] = value & 0xff;
  target[1] = (value >> 8) & 0xff;
  target[2] = (value >> 16) & 0xff;
  target[3] = (value >> 24) & 0xff;
}

void putUint16LE(uint8_t* target, uint16_t value) {
  target[0] = value & 0xff;
  target[1] = (value >> 8) & 0xff;
}

void makeWavHeader(uint8_t* header, size_t pcm_bytes) {
  memset(header, 0, 44);
  memcpy(header, "RIFF", 4);
  putUint32LE(header + 4, 36 + pcm_bytes);
  memcpy(header + 8, "WAVEfmt ", 8);
  putUint32LE(header + 16, 16);
  putUint16LE(header + 20, 1);
  putUint16LE(header + 22, 1);
  putUint32LE(header + 24, lantern::kAudioSampleRateHz);
  putUint32LE(header + 28, lantern::kAudioSampleRateHz * 2);
  putUint16LE(header + 32, 2);
  putUint16LE(header + 34, 16);
  memcpy(header + 36, "data", 4);
  putUint32LE(header + 40, pcm_bytes);
}
}  // namespace

void BackendTransport::begin() {
  WiFi.mode(WIFI_STA);
  ensureWiFi();
}

bool BackendTransport::ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  if (strlen(LANTERN_WIFI_SSID) == 0) {
    Serial.println("Wi-Fi credentials are not configured in secrets.h");
    return false;
  }

  Serial.printf("Connecting to Wi-Fi: %s\n", LANTERN_WIFI_SSID);
  WiFi.begin(LANTERN_WIFI_SSID, LANTERN_WIFI_PASSWORD);
  const uint32_t started_at = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started_at < kWifiTimeoutMs) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi connection timed out; will retry before upload");
    return false;
  }
  Serial.print("Wi-Fi connected, IP: ");
  Serial.println(WiFi.localIP());
  return true;
}

bool BackendTransport::sendWav(
    const int16_t* samples,
    size_t sample_count,
    String* response) {
  if (samples == nullptr || sample_count == 0 || response == nullptr) {
    return false;
  }
  if (!ensureWiFi()) return false;

  WiFiClient client;
  client.setTimeout(kHttpTimeoutMs);
  if (!client.connect(LANTERN_BACKEND_HOST, LANTERN_BACKEND_PORT)) {
    Serial.println("Backend connection failed");
    return false;
  }

  const size_t pcm_bytes = sample_count * sizeof(int16_t);
  const size_t wav_bytes = 44 + pcm_bytes;
  const String prefix = String("--") + kBoundary +
      "\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"utterance.wav\"\r\n"
      "Content-Type: audio/wav\r\n\r\n";
  const String suffix = String("\r\n--") + kBoundary + "--\r\n";
  const size_t content_length = prefix.length() + wav_bytes + suffix.length();

  client.print(String("POST ") + LANTERN_BACKEND_PATH + " HTTP/1.1\r\n");
  client.print(String("Host: ") + LANTERN_BACKEND_HOST + "\r\n");
  client.print(String("Content-Type: multipart/form-data; boundary=") +
               kBoundary + "\r\n");
  client.print(String("Content-Length: ") + content_length + "\r\n");
  client.print("Connection: close\r\n\r\n");

  uint8_t wav_header[44];
  makeWavHeader(wav_header, pcm_bytes);
  if (!writeString(client, prefix) || !writeBytes(client, wav_header, sizeof(wav_header)) ||
      !writeBytes(client, reinterpret_cast<const uint8_t*>(samples), pcm_bytes) ||
      !writeString(client, suffix)) {
    Serial.println("Audio upload write failed");
    client.stop();
    return false;
  }

  const String status_line = client.readStringUntil('\n');
  const int status_code = status_line.substring(9, 12).toInt();
  while (client.connected()) {
    const String line = client.readStringUntil('\n');
    if (line == "\r" || line.length() == 0) break;
  }
  *response = "";
  const uint32_t response_started_at = millis();
  while ((client.connected() || client.available()) &&
         millis() - response_started_at < kHttpTimeoutMs && response->length() < 2048) {
    if (client.available()) {
      *response += static_cast<char>(client.read());
    } else {
      delay(1);
    }
  }
  client.stop();
  Serial.printf("Backend HTTP status: %d\n", status_code);
  return status_code >= 200 && status_code < 300;
}
