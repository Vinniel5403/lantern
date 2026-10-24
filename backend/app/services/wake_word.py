from __future__ import annotations

from dataclasses import dataclass

from app.services.text_normalization import normalize_text


DEFAULT_THAI_WAKE_WORD = "\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e23\u0e4c\u0e19"
DEFAULT_WAKE_ALTERNATIVES = (
    "lantern",
    "\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e19",
    "\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e48\u0e19",
    "\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e23\u0e19",
)


@dataclass(frozen=True)
class WakeWordMatch:
    detected: bool
    normalized_text: str
    matched_phrase: str | None = None
    command_text: str = ""


@dataclass(frozen=True)
class WakeWordVerifier:
    """Transcript-level wake-word verifier; on-device wake word is not claimed."""

    phrase: str = DEFAULT_THAI_WAKE_WORD
    alternatives: tuple[str, ...] = DEFAULT_WAKE_ALTERNATIVES

    def _candidates(self) -> tuple[str, ...]:
        candidates = {
            normalized
            for value in (self.phrase, *self.alternatives)
            if (normalized := normalize_text(value))
        }
        return tuple(sorted(candidates, key=len, reverse=True))

    def match(self, transcript: str) -> WakeWordMatch:
        normalized = normalize_text(transcript)
        for candidate in self._candidates():
            if not normalized.startswith(candidate):
                continue

            remainder = normalized[len(candidate) :]
            if (
                remainder
                and candidate[-1].isascii()
                and candidate[-1].isalnum()
                and remainder[0].isascii()
                and remainder[0].isalnum()
            ):
                continue
            return WakeWordMatch(
                detected=True,
                normalized_text=normalized,
                matched_phrase=candidate,
                command_text=normalize_text(remainder),
            )

        return WakeWordMatch(detected=False, normalized_text=normalized)

    def verify(self, transcript: str) -> bool:
        return self.match(transcript).detected
