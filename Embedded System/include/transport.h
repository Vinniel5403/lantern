#pragma once

#include <Arduino.h>

class BackendTransport {
 public:
  void begin();
  bool sendWav(const int16_t* samples, size_t sample_count, String* response);

 private:
  bool ensureWiFi();
};
