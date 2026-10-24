#pragma once

#include <Arduino.h>

class CommandHandler {
 public:
  void begin();
  void handleBackendResponse(const String& response);
  void handleSerialCommand(const String& command);

 private:
  void setDemoLed(bool enabled);
  String last_executed_request_id_;
};
