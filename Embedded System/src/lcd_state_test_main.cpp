#include <Arduino.h>

#include "lcd_controller.h"

namespace {
constexpr DisplayState kStates[] = {
    DisplayState::LISTENING,
    DisplayState::RECORDING,
    DisplayState::PROCESSING,
    DisplayState::WIFI_DISCONNECTED,
    DisplayState::LIGHT_ON,
    DisplayState::LIGHT_OFF,
};
constexpr size_t kStateCount = sizeof(kStates) / sizeof(kStates[0]);
constexpr uint32_t kStateIntervalMs = 1500;

LcdController lcd;
size_t state_index = 0;
uint32_t next_state_ms = 0;
}

void setup() {
  Serial.begin(115200);
  Serial.println("Lantern LCD state diagnostic mode");
  Serial.println("No relay, I2S, Wi-Fi, HTTP, ASR, or voice pipeline initialized");

  if (!lcd.begin()) {
    Serial.println("LCD state diagnostic unavailable");
    return;
  }

  lcd.setState(kStates[state_index]);
  Serial.printf(
      "[LCD DIAGNOSTIC] state=%s\n",
      LcdController::stateName(kStates[state_index]));
  next_state_ms = millis() + kStateIntervalMs;
}

void loop() {
  lcd.tick();
  if (!lcd.available() ||
      static_cast<int32_t>(millis() - next_state_ms) < 0) {
    return;
  }

  state_index = (state_index + 1) % kStateCount;
  lcd.setState(kStates[state_index]);
  Serial.printf(
      "[LCD DIAGNOSTIC] state=%s\n",
      LcdController::stateName(kStates[state_index]));
  next_state_ms = millis() + kStateIntervalMs;
}
