#pragma once

#include <Arduino.h>

class BackendTransport {
 public:
  enum class FailureReason : uint8_t {
    kNone,
    kInvalidAudio,
    kWifiDisconnected,
    kNetworkError,
    kHttpTimeout,
    kBackendRejected,
    kAsrFailure,
    kBackendError,
  };

  void begin();
  bool sendWavFile(const char* pcm_path, size_t sample_count, String* response);
  FailureReason lastFailureReason() const { return last_failure_reason_; }
  static const char* failureReasonName(FailureReason reason);

 private:
  enum class AttemptResult { kSuccess, kRetryableFailure, kPermanentFailure };

  bool ensureWiFi();
  AttemptResult sendWavAttempt(
      const char* pcm_path,
      size_t sample_count,
      const String& request_id,
      String* response);
  String nextRequestId();

  FailureReason last_failure_reason_ = FailureReason::kNone;
};
