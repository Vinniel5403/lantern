#pragma once

#include <Arduino.h>

enum class DisplayState : uint8_t {
  BOOTING,
  IDLE,
  LISTENING,
  RECORDING,
  PROCESSING,
  COMMAND_ACCEPTED,
  COMMAND_REJECTED,
  LIGHT_ON,
  LIGHT_OFF,
  WIFI_DISCONNECTED,
  BACKEND_ERROR,
};

class LcdController {
 public:
  bool begin();
  void tick();
  void setState(
      DisplayState state,
      const char* detail = nullptr,
      uint32_t hold_ms = 0);
  void showText(const char* line1, const char* line2);

  bool available() const { return available_; }
  bool holdingMessage() const { return hold_until_ms_ != 0; }
  uint8_t address() const { return address_; }
  DisplayState state() const { return state_; }

  static const char* stateName(DisplayState state);

 private:
  bool scanAddress(uint8_t address);
  bool writeExpander(uint8_t value);
  void initializeController();
  void writeCommand(uint8_t command);
  void writeData(uint8_t value);
  void write4Bits(uint8_t nibble, bool data_mode);
  void render();
  void renderLine(uint8_t row, const String& value);
  void makeMessage(String* line1, String* line2) const;

  bool available_ = false;
  bool error_logged_ = false;
  bool backlight_ = true;
  uint8_t address_ = 0;
  DisplayState state_ = DisplayState::BOOTING;
  uint32_t hold_until_ms_ = 0;
  String detail_;
  String last_line1_;
  String last_line2_;
};
