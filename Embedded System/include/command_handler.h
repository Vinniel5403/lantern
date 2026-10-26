#pragma once

#include <Arduino.h>

#include "lantern_config.h"
#include "relay_controller.h"

enum class CommandResult : uint8_t {
  kRejected,
  kInvalid,
  kLightOn,
  kLightOff,
};

class CommandHandler {
 public:
  void begin(RelayController* relay_controller = nullptr);
  CommandResult handleBackendResponse(const String& response);
  void handleSerialCommand(const String& command);

 private:
  void setDemoLed(bool enabled);
  bool hasExecutedRequest(const String& request_id) const;
  void rememberExecutedRequest(const String& request_id);

  String executed_request_ids_[lantern::kExecutedRequestCacheSize];
  uint8_t executed_request_count_ = 0;
  uint8_t executed_request_next_ = 0;
  RelayController* relay_controller_ = nullptr;
};
