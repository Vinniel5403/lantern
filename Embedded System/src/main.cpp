#include <Arduino.h>

#include "audio_capture.h"
#include "audio_filter.h"
#include "command_handler.h"
#include "lantern_config.h"
#include "transport.h"
#include "utterance_segmenter.h"
#include "vad.h"

AudioCapture audio_capture;
AudioFilter audio_filter;
VoiceActivityGate vad;
BackendTransport transport;
CommandHandler command_handler;
UtteranceSegmenter segmenter;
int16_t audio_frame[lantern::kAudioFrameSamples] = {};

void printSignalTelemetry(
    const int16_t* samples,
    size_t sample_count,
    bool speech,
    bool recording) {
  static uint32_t last_print_ms = 0;
  const uint32_t now_ms = millis();
  if (now_ms - last_print_ms < lantern::kSignalTelemetryIntervalMs) return;
  last_print_ms = now_ms;

  if (samples == nullptr || sample_count == 0) return;

  uint64_t absolute_sum = 0;
  int16_t minimum = 32767;
  int16_t maximum = -32768;
  uint16_t peak = 0;
  for (size_t index = 0; index < sample_count; ++index) {
    const int16_t sample = samples[index];
    const uint16_t magnitude = static_cast<uint16_t>(
        sample < 0 ? -static_cast<int32_t>(sample) : sample);
    absolute_sum += magnitude;
    if (magnitude > peak) peak = magnitude;
    if (sample < minimum) minimum = sample;
    if (sample > maximum) maximum = sample;
  }

  const uint32_t mean_absolute =
      static_cast<uint32_t>(absolute_sum / sample_count);
  Serial.printf(
      "INMP441 signal mean=%lu peak=%u min=%d max=%d vad=%s recording=%s "
      "free_heap=%lu\n",
      static_cast<unsigned long>(mean_absolute),
      peak,
      minimum,
      maximum,
      speech ? "SPEECH" : "silence",
      recording ? "yes" : "no",
      static_cast<unsigned long>(ESP.getFreeHeap()));
}

void setup() {
  Serial.begin(115200);
  pinMode(lantern::pins::kDemoLed, OUTPUT);
  digitalWrite(lantern::pins::kDemoLed, LOW);
  audio_capture.begin();
  audio_filter.reset();
  transport.begin();
  command_handler.begin();
  segmenter.reset();
  Serial.println("Lantern Phase 2 firmware ready: hands-free I2S capture");
  Serial.println("Audio is sent as bounded WAV utterances; no push-to-talk input.");
  Serial.println("INMP441 telemetry: mean/peak/min/max every 1 second");
  Serial.println("Audio filter: high-pass plus noise gate");
}

void loop() {
  size_t samples_read = 0;
  if (!audio_capture.readFrame(
          audio_frame,
          lantern::kAudioFrameSamples,
          &samples_read)) {
    Serial.println("I2S frame read failed");
    delay(100);
    return;
  }

  audio_filter.process(audio_frame, samples_read);
  const bool speech = vad.speechDetected(audio_frame, samples_read);
  const bool utterance_complete =
      segmenter.processFrame(audio_frame, samples_read, speech);
  printSignalTelemetry(
      audio_frame, samples_read, speech, segmenter.active());
  if (!utterance_complete) return;

  String response;
  if (!transport.sendWav(segmenter.samples(), segmenter.sampleCount(), &response)) {
    Serial.println("Utterance upload failed; continuing to listen");
  } else {
    command_handler.handleBackendResponse(response);
  }
  segmenter.reset();
}
