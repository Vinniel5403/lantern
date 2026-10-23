#include "command_handler.h"

void CommandHandler::begin() {
  Serial.println("Command handler ready; no mains actuator is enabled in Phase 2");
}

void CommandHandler::handleBackendResponse(const String& response) {
  Serial.print("Backend response: ");
  Serial.println(response);
}
