#pragma once

#include <Arduino.h>

#include "lantern_config.h"

class UtteranceSegmenter {
 public:
  void reset();
  bool processFrame(const int16_t* samples, size_t sample_count, bool speech);
  bool flush();

  bool active() const { return recording_; }
  const int16_t* samples() const { return utterance_; }
  size_t sampleCount() const { return utterance_sample_count_; }

 private:
  void pushPreRoll(const int16_t* samples, size_t sample_count);
  void copyPreRollToUtterance();
  bool appendToUtterance(const int16_t* samples, size_t sample_count);
  void clearState();

  int16_t pre_roll_[lantern::kPreRollSamples] = {};
  size_t pre_roll_count_ = 0;
  size_t pre_roll_write_index_ = 0;
  int16_t utterance_[lantern::kMaxRecordingSamples] = {};
  size_t utterance_sample_count_ = 0;
  uint16_t speech_ms_ = 0;
  uint16_t silence_ms_ = 0;
  uint16_t recording_ms_ = 0;
  bool recording_ = false;
};
