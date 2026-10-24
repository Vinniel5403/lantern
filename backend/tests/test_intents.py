import pytest

from app.services.intents import IntentDetector


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("เปิดไฟหน่อย", "LIGHT_ON"),
        ("ดับไฟ", "LIGHT_OFF"),
        ("เปิดพัดลม", "FAN_ON"),
        ("หยุดพัดลม", "FAN_OFF"),
    ],
)
def test_allowlisted_thai_commands(command: str, expected: str) -> None:
    decision = IntentDetector().detect(command)

    assert decision.name == expected
    assert decision.accepted is True


def test_unknown_command_is_rejected() -> None:
    decision = IntentDetector().detect("วันนี้อากาศดี")

    assert decision.name == "UNKNOWN_INTENT"
    assert decision.accepted is False


def test_contradictory_command_is_rejected() -> None:
    decision = IntentDetector().detect("เปิดไฟแล้วปิดไฟ")

    assert decision.name == "UNKNOWN_INTENT"
    assert decision.reason == "contradictory commands"


def test_multiple_device_commands_are_rejected() -> None:
    decision = IntentDetector().detect("เปิดไฟและเปิดพัดลม")

    assert decision.name == "UNKNOWN_INTENT"
    assert decision.reason == "ambiguous multiple commands"


def test_negative_command_is_rejected() -> None:
    decision = IntentDetector().detect("อย่าเปิดไฟ")

    assert decision.name == "UNKNOWN_INTENT"
    assert decision.accepted is False
