#pragma once

#include <Arduino.h>

class CommandHandler {
 public:
  void begin();
  void handleBackendResponse(const String& response);
};
