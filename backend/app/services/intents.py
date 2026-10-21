from dataclasses import dataclass

from app.schemas import IntentDecision


@dataclass(frozen=True)
class IntentDetector:
    """Small deterministic allowlist for safe command routing."""

    def detect(self, transcript: str) -> IntentDecision:
        text = transcript.casefold().replace("lantern", "").strip()
        if "เปิดไฟ" in text or "เปิด ไฟ" in text:
            return IntentDecision(
                name="LIGHT_ON",
                parameters={"output": "demo_led"},
                accepted=True,
                reason="allowlisted command",
            )
        if "ปิดไฟ" in text or "ปิด ไฟ" in text:
            return IntentDecision(
                name="LIGHT_OFF",
                parameters={"output": "demo_led"},
                accepted=True,
                reason="allowlisted command",
            )
        return IntentDecision(reason="no allowlisted intent matched")
