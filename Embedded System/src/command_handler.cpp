#include "command_handler.h"

#include "lantern_config.h"

namespace {
bool containsIntent(const String& response, const char* intent) {
  const String compact = String("\"name\":\"") + intent + "\"";
  const String spaced = String("\"name\": \"") + intent + "\"";
  return response.indexOf(compact) >= 0 || response.indexOf(spaced) >= 0;
}

bool isAccepted(const String& response) {
  return response.indexOf("\"accepted\":true") >= 0 ||
         response.indexOf("\"accepted\": true") >= 0;
}

String extractRequestId(const String& response) {
  const String marker = "\"request_id\":\"";
  const int start = response.indexOf(marker);
  if (start < 0) return "";
  const int value_start = start + marker.length();
  const int value_end = response.indexOf('"', value_start);
  if (value_end < 0) return "";
  return response.substring(value_start, value_end);
}
}  // namespace

void CommandHandler::begin() {
  pinMode(lantern::pins::kDemoLed, OUTPUT);
  setDemoLed(false);
  Serial.println("Command handler ready; low-voltage demo LED on GPIO17");
  Serial.println("Serial test commands: LED ON, LED OFF");
}

void CommandHandler::setDemoLed(bool enabled) {
  digitalWrite(lantern::pins::kDemoLed, enabled ? HIGH : LOW);
  Serial.printf("Demo LED: %s\n", enabled ? "ON" : "OFF");
}

void CommandHandler::handleSerialCommand(const String& command) {
  String normalized = command;
  normalized.trim();
  normalized.toUpperCase();
  if (normalized == "LED ON" || normalized == "ON") {
    setDemoLed(true);
  } else if (normalized == "LED OFF" || normalized == "OFF") {
    setDemoLed(false);
  } else {
    Serial.println("Unknown LED command; use LED ON or LED OFF");
  }
}

void CommandHandler::handleBackendResponse(const String& response) {
  Serial.print("Backend response: ");
  Serial.println(response);
  if (!isAccepted(response)) {
    Serial.println("No LED action accepted by backend response");
    return;
  }
  const String request_id = extractRequestId(response);
  if (request_id.length() > 0 && request_id == last_executed_request_id_) {
    Serial.printf("Duplicate backend response ignored request_id=%s\n",
                  request_id.c_str());
    return;
  }
  if (containsIntent(response, "LIGHT_ON")) {
    last_executed_request_id_ = request_id;
    setDemoLed(true);
  } else if (containsIntent(response, "LIGHT_OFF")) {
    last_executed_request_id_ = request_id;
    setDemoLed(false);
  } else {
    Serial.println("No LED action accepted by backend response");
  }
}
