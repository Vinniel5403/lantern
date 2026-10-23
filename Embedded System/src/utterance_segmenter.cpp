#include "utterance_segmenter.h"

#include <string.h>

#include "lantern_config.h"

void UtteranceSegmenter::reset() {
  pre_roll_count_ = 0;
  pre_roll_write_index_ = 0;
  clearState();
}

bool UtteranceSegmenter::processFrame(
    const int16_t* samples,
    size_t sample_count,
    bool speech) {
  if (samples == nullptr || sample_count != lantern::kAudioFrameSamples) {
    return false;
  }

  if (!recording_) {
    pushPreRoll(samples, sample_count);
    if (!speech) return false;

    recording_ = true;
    utterance_sample_count_ = 0;
    copyPreRollToUtterance();
    speech_ms_ = lantern::kAudioFrameMs;
    silence_ms_ = 0;
    recording_ms_ =
        static_cast<uint16_t>(utterance_sample_count_ * 1000 /
                              lantern::kAudioSampleRateHz);
    return false;
  }

  if (!appendToUtterance(samples, sample_count)) {
    recording_ = false;
    return speech_ms_ >= lantern::kMinimumSpeechMs;
  }
  recording_ms_ += lantern::kAudioFrameMs;
  if (speech) {
    speech_ms_ += lantern::kAudioFrameMs;
    silence_ms_ = 0;
  } else {
    silence_ms_ += lantern::kAudioFrameMs;
  }

  if (silence_ms_ >= lantern::kSilenceTimeoutMs ||
      recording_ms_ >= lantern::kMaxRecordingMs) {
    recording_ = false;
    if (speech_ms_ >= lantern::kMinimumSpeechMs) return true;
    clearState();
  }
  return false;
}

bool UtteranceSegmenter::flush() {
  if (!recording_) return false;
  recording_ = false;
  if (speech_ms_ >= lantern::kMinimumSpeechMs) return true;
  clearState();
  return false;
}

void UtteranceSegmenter::pushPreRoll(
    const int16_t* samples,
    size_t sample_count) {
  for (size_t index = 0; index < sample_count; ++index) {
    if (pre_roll_count_ < lantern::kPreRollSamples) {
      pre_roll_[pre_roll_count_++] = samples[index];
    } else {
      pre_roll_[pre_roll_write_index_] = samples[index];
      pre_roll_write_index_ =
          (pre_roll_write_index_ + 1) % lantern::kPreRollSamples;
    }
  }
}

void UtteranceSegmenter::copyPreRollToUtterance() {
  if (pre_roll_count_ == 0) return;
  const size_t start = pre_roll_count_ == lantern::kPreRollSamples
                           ? pre_roll_write_index_
                           : 0;
  for (size_t index = 0; index < pre_roll_count_; ++index) {
    if (!appendToUtterance(
            &pre_roll_[(start + index) % lantern::kPreRollSamples], 1)) {
      return;
    }
  }
}

bool UtteranceSegmenter::appendToUtterance(
    const int16_t* samples,
    size_t sample_count) {
  if (utterance_sample_count_ + sample_count > lantern::kMaxRecordingSamples) {
    return false;
  }
  memcpy(
      &utterance_[utterance_sample_count_],
      samples,
      sample_count * sizeof(int16_t));
  utterance_sample_count_ += sample_count;
  return true;
}

void UtteranceSegmenter::clearState() {
  pre_roll_count_ = 0;
  pre_roll_write_index_ = 0;
  utterance_sample_count_ = 0;
  speech_ms_ = 0;
  silence_ms_ = 0;
  recording_ms_ = 0;
  recording_ = false;
}
