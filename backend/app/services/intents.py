from __future__ import annotations

from dataclasses import dataclass

from app.schemas import IntentDecision
from app.services.text_normalization import compact_text


_COMMANDS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "LIGHT_ON",
        (
            "\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f",  # เปิดไฟ
            "\u0e40\u0e1b\u0e34\u0e14\u0e2b\u0e25\u0e2d\u0e14\u0e44\u0e1f",  # เปิดหลอดไฟ
            "turnonlight",
            "lighton",
        ),
        "demo_led",
    ),
    (
        "LIGHT_OFF",
        (
            "\u0e1b\u0e34\u0e14\u0e44\u0e1f",  # ปิดไฟ
            "\u0e14\u0e31\u0e1a\u0e44\u0e1f",  # ดับไฟ
            "\u0e1b\u0e34\u0e14\u0e2b\u0e25\u0e2d\u0e14\u0e44\u0e1f",  # ปิดหลอดไฟ
            "turnofflight",
            "lightoff",
        ),
        "demo_led",
    ),
    (
        "FAN_ON",
        (
            "\u0e40\u0e1b\u0e34\u0e14\u0e1e\u0e31\u0e14\u0e25\u0e21",  # เปิดพัดลม
            "turnonfan",
            "fanon",
        ),
        "demo_fan",
    ),
    (
        "FAN_OFF",
        (
            "\u0e1b\u0e34\u0e14\u0e1e\u0e31\u0e14\u0e25\u0e21",  # ปิดพัดลม
            "\u0e2b\u0e22\u0e38\u0e14\u0e1e\u0e31\u0e14\u0e25\u0e21",  # หยุดพัดลม
            "turnofffan",
            "fanoff",
        ),
        "demo_fan",
    ),
)
_NEGATIONS = ("\u0e44\u0e21\u0e48", "\u0e2d\u0e22\u0e48\u0e32", "\u0e2b\u0e49\u0e32\u0e21")


def _contains_pattern(text: str, pattern: str) -> bool:
    """Match Thai phrases without treating the ปิด part of เปิด as a command."""
    start = 0
    while True:
        index = text.find(pattern, start)
        if index < 0:
            return False
        if not pattern.startswith("\u0e1b\u0e34\u0e14") or index == 0:
            return True
        # Thai leading เ in เปิด precedes the ปิด-looking substring.
        if text[index - 1] != "\u0e40":
            return True
        start = index + 1


def _unknown(reason: str) -> IntentDecision:
    return IntentDecision(name="UNKNOWN_INTENT", accepted=False, reason=reason)


@dataclass(frozen=True)
class IntentDetector:
    """Deterministic allowlist for safe command routing."""

    def detect(self, command: str) -> IntentDecision:
        compact = compact_text(command)
        if not compact:
            return _unknown("empty command after wake word")

        matches = [
            (name, output)
            for name, patterns, output in _COMMANDS
            if any(_contains_pattern(compact, pattern) for pattern in patterns)
        ]

        if not matches:
            return _unknown("no allowlisted intent matched")

        if any(negation in compact for negation in _NEGATIONS):
            return _unknown("negative command is not accepted")

        distinct_names = {name for name, _ in matches}
        if len(distinct_names) > 1:
            devices = {output for _, output in matches}
            reason = (
                "contradictory commands"
                if len(devices) < len(distinct_names)
                else "ambiguous multiple commands"
            )
            return _unknown(reason)

        name, output = matches[0]
        return IntentDecision(
            name=name,
            parameters={"output": output},
            accepted=True,
            reason="allowlisted command",
        )
