#include "lcd_controller.h"

#include <Wire.h>

#include "lantern_config.h"

namespace {
constexpr uint8_t kRs = 0x01;
constexpr uint8_t kEnable = 0x04;
constexpr uint8_t kBacklight = 0x08;
constexpr uint8_t kFirstPcf8574Address = 0x20;
constexpr uint8_t kLastPcf8574Address = 0x27;
constexpr uint8_t kFirstPcf8574aAddress = 0x38;
constexpr uint8_t kLastPcf8574aAddress = 0x3F;
constexpr uint8_t kColumns = 16;

String clipped(const String& value) {
  if (value.length() <= kColumns) return value;
  return value.substring(0, kColumns);
}
}  // namespace

bool LcdController::begin() {
  Wire.begin(lantern::kLcdSda, lantern::kLcdScl);
  Serial.printf(
      "LCD I2C scan: SDA=%u SCL=%u preferred=0x%02X\n",
      lantern::kLcdSda,
      lantern::kLcdScl,
      lantern::kLcdPreferredAddress);

  bool preferred_found = false;
  for (uint8_t candidate = kFirstPcf8574Address;
       candidate <= kLastPcf8574Address;
       ++candidate) {
    if (!scanAddress(candidate)) continue;
    if (candidate == lantern::kLcdPreferredAddress) preferred_found = true;
    if (address_ == 0 || candidate == lantern::kLcdPreferredAddress) {
      address_ = candidate;
    }
  }
  for (uint8_t candidate = kFirstPcf8574aAddress;
       candidate <= kLastPcf8574aAddress;
       ++candidate) {
    if (!scanAddress(candidate)) continue;
    if (address_ == 0) address_ = candidate;
  }

  if (address_ == 0) {
    Serial.println(
        "LCD unavailable: no I2C device detected; voice pipeline continues");
    return false;
  }

  available_ = true;
  initializeController();
  Serial.printf(
      "LCD selected at I2C address 0x%02X%s\n",
      address_,
      preferred_found ? " (preferred)" : " (fallback)");
  setState(DisplayState::BOOTING, "LCD ONLINE");
  return available_;
}

void LcdController::tick() {
  if (hold_until_ms_ == 0) return;
  if (static_cast<int32_t>(millis() - hold_until_ms_) < 0) return;

  hold_until_ms_ = 0;
  if (state_ == DisplayState::WIFI_DISCONNECTED) {
    setState(DisplayState::WIFI_DISCONNECTED, "RECONNECTING");
    return;
  }
  setState(DisplayState::IDLE, "SAY TEE");
}

void LcdController::setState(
    DisplayState state,
    const char* detail,
    uint32_t hold_ms) {
  if (state_ != state) {
    Serial.printf(
        "[LCD] %s -> %s\n",
        stateName(state_),
        stateName(state));
  }
  state_ = state;
  detail_ = detail == nullptr ? "" : detail;
  hold_until_ms_ = hold_ms == 0 ? 0 : millis() + hold_ms;
  render();
}

void LcdController::showText(const char* line1, const char* line2) {
  if (!available_) return;

  const String next_line1 = clipped(line1 == nullptr ? "" : line1);
  const String next_line2 = clipped(line2 == nullptr ? "" : line2);
  if (next_line1 == last_line1_ && next_line2 == last_line2_) return;

  renderLine(0, next_line1);
  renderLine(1, next_line2);
  last_line1_ = next_line1;
  last_line2_ = next_line2;
  Serial.printf(
      "LCD text line1=%s line2=%s\n",
      next_line1.c_str(),
      next_line2.c_str());
}

const char* LcdController::stateName(DisplayState state) {
  switch (state) {
    case DisplayState::BOOTING:
      return "BOOTING";
    case DisplayState::IDLE:
      return "IDLE";
    case DisplayState::LISTENING:
      return "LISTENING";
    case DisplayState::RECORDING:
      return "RECORDING";
    case DisplayState::PROCESSING:
      return "PROCESSING";
    case DisplayState::COMMAND_ACCEPTED:
      return "COMMAND_ACCEPTED";
    case DisplayState::COMMAND_REJECTED:
      return "COMMAND_REJECTED";
    case DisplayState::LIGHT_ON:
      return "LIGHT_ON";
    case DisplayState::LIGHT_OFF:
      return "LIGHT_OFF";
    case DisplayState::WIFI_DISCONNECTED:
      return "WIFI_DISCONNECTED";
    case DisplayState::BACKEND_ERROR:
      return "BACKEND_ERROR";
    default:
      return "UNKNOWN";
  }
}

bool LcdController::scanAddress(uint8_t address) {
  Wire.beginTransmission(address);
  const uint8_t error = Wire.endTransmission();
  if (error == 0) {
    Serial.printf("LCD I2C device found at 0x%02X\n", address);
    return true;
  }
  return false;
}

bool LcdController::writeExpander(uint8_t value) {
  Wire.beginTransmission(address_);
  Wire.write(value | (backlight_ ? kBacklight : 0));
  const uint8_t error = Wire.endTransmission();
  if (error != 0) {
    available_ = false;
    if (!error_logged_) {
      Serial.printf("LCD I2C write failed: error=%u\n", error);
      error_logged_ = true;
    }
    return false;
  }
  return true;
}

void LcdController::initializeController() {
  delay(50);
  write4Bits(0x03, false);
  delayMicroseconds(4500);
  write4Bits(0x03, false);
  delayMicroseconds(4500);
  write4Bits(0x03, false);
  delayMicroseconds(150);
  write4Bits(0x02, false);

  writeCommand(0x28);  // 4-bit, 2-line, 5x8 font.
  writeCommand(0x08);  // Display off while initializing.
  writeCommand(0x01);  // Clear once during initialization only.
  delay(2);
  writeCommand(0x06);  // Increment cursor, no display shift.
  writeCommand(0x0C);  // Display on, cursor and blink off.
}

void LcdController::writeCommand(uint8_t command) {
  write4Bits(command >> 4, false);
  write4Bits(command & 0x0F, false);
}

void LcdController::writeData(uint8_t value) {
  write4Bits(value >> 4, true);
  write4Bits(value & 0x0F, true);
}

void LcdController::write4Bits(uint8_t nibble, bool data_mode) {
  const uint8_t packet = static_cast<uint8_t>(
      ((nibble & 0x0F) << 4) | (data_mode ? kRs : 0));
  writeExpander(packet);
  writeExpander(packet | kEnable);
  delayMicroseconds(1);
  writeExpander(packet & static_cast<uint8_t>(~kEnable));
  delayMicroseconds(40);
}

void LcdController::render() {
  if (!available_) return;

  String line1;
  String line2;
  makeMessage(&line1, &line2);
  line1 = clipped(line1);
  line2 = clipped(line2);
  if (line1 == last_line1_ && line2 == last_line2_) return;

  renderLine(0, line1);
  renderLine(1, line2);
  last_line1_ = line1;
  last_line2_ = line2;
  Serial.printf(
      "LCD state=%s line1=%s line2=%s\n",
      stateName(state_),
      line1.c_str(),
      line2.c_str());
}

void LcdController::renderLine(uint8_t row, const String& value) {
  writeCommand(row == 0 ? 0x80 : 0xC0);
  for (uint8_t index = 0; index < kColumns; ++index) {
    writeData(index < value.length() ? value[index] : ' ');
  }
}

void LcdController::makeMessage(String* line1, String* line2) const {
  *line2 = detail_;
  switch (state_) {
    case DisplayState::BOOTING:
      *line1 = "LANTERN BOOTING";
      if (line2->length() == 0) *line2 = "STARTING";
      break;
    case DisplayState::IDLE:
      *line1 = "READY";
      if (line2->length() == 0) *line2 = "SAY TEE";
      break;
    case DisplayState::LISTENING:
      *line1 = "LISTENING";
      if (line2->length() == 0) *line2 = "WAITING SPEECH";
      break;
    case DisplayState::RECORDING:
      *line1 = "RECORDING";
      if (line2->length() == 0) *line2 = "CAPTURING";
      break;
    case DisplayState::PROCESSING:
      *line1 = "PROCESSING";
      if (line2->length() == 0) *line2 = "ASR + INTENT";
      break;
    case DisplayState::COMMAND_ACCEPTED:
      *line1 = "COMMAND OK";
      if (line2->length() == 0) *line2 = "ACCEPTED";
      break;
    case DisplayState::COMMAND_REJECTED:
      *line1 = "COMMAND NO";
      if (line2->length() == 0) *line2 = "REJECTED";
      break;
    case DisplayState::LIGHT_ON:
      *line1 = "LIGHT ON";
      if (line2->length() == 0) *line2 = "RELAY DISPATCHED";
      break;
    case DisplayState::LIGHT_OFF:
      *line1 = "LIGHT OFF";
      if (line2->length() == 0) *line2 = "RELAY DISPATCHED";
      break;
    case DisplayState::WIFI_DISCONNECTED:
      *line1 = "WIFI OFFLINE";
      if (line2->length() == 0) *line2 = "RECONNECTING";
      break;
    case DisplayState::BACKEND_ERROR:
      *line1 = "BACKEND ERROR";
      if (line2->length() == 0) *line2 = "CHECK SERVER";
      break;
    default:
      *line1 = "LANTERN";
      if (line2->length() == 0) *line2 = "UNKNOWN STATE";
      break;
  }
}
