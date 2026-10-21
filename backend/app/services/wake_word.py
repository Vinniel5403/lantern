from dataclasses import dataclass


@dataclass(frozen=True)
class WakeWordVerifier:
    """Initial transcript-level verifier; on-device wake word is not claimed."""

    phrase: str = "lantern"

    def verify(self, transcript: str) -> bool:
        return self.phrase.casefold() in transcript.casefold()
