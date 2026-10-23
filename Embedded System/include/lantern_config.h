#pragma once

#include <Arduino.h>

#if __has_include("secrets.h")
#include "secrets.h"
#endif

#ifndef LANTERN_WIFI_SSID
#define LANTERN_WIFI_SSID ""
#endif

#ifndef LANTERN_WIFI_PASSWORD
#define LANTERN_WIFI_PASSWORD ""
#endif

#ifndef LANTERN_BACKEND_HOST
#define LANTERN_BACKEND_HOST "192.168.137.1"
#endif

#ifndef LANTERN_BACKEND_PORT
#define LANTERN_BACKEND_PORT 8000
#endif

#ifndef LANTERN_BACKEND_PATH
#define LANTERN_BACKEND_PATH "/v1/utterances/transcribe"
#endif

namespace lantern {
namespace pins {
constexpr gpio_num_t kI2sBclk = GPIO_NUM_26;
constexpr gpio_num_t kI2sWs = GPIO_NUM_25;
constexpr gpio_num_t kI2sDataIn = GPIO_NUM_33;
constexpr uint8_t kDemoLed = 2;
}  // namespace pins

constexpr uint32_t kAudioSampleRateHz = 16000;
constexpr uint16_t kAudioFrameMs = 20;
constexpr size_t kAudioFrameSamples =
    kAudioSampleRateHz * kAudioFrameMs / 1000;
constexpr uint16_t kPreRollMs = 300;
constexpr size_t kPreRollSamples = kAudioSampleRateHz * kPreRollMs / 1000;
constexpr uint16_t kSilenceTimeoutMs = 1000;
constexpr uint16_t kMinimumSpeechMs = 200;
// Keep the complete WAV in internal DRAM; ESP32 DevKit V1 does not guarantee PSRAM.
constexpr uint16_t kMaxRecordingMs = 2000;
constexpr size_t kMaxRecordingSamples =
    kAudioSampleRateHz * kMaxRecordingMs / 1000;
constexpr uint16_t kVadMeanAbsoluteThreshold = 700;
// Lightweight preprocessing for INMP441 input. Increase the gate only if the
// physical microphone setup has a consistently loud noise floor.
constexpr uint16_t kNoiseGateThreshold = 120;
constexpr int32_t kHighPassFeedbackNumerator = 995;
constexpr int32_t kHighPassFeedbackDenominator = 1000;
constexpr uint32_t kSignalTelemetryIntervalMs = 1000;
}  // namespace lantern
