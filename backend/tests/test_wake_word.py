from app.services.wake_word import WakeWordVerifier


def test_thai_wake_word_extracts_command_without_spaces() -> None:
    match = WakeWordVerifier().match("\u0e41\u0e25\u0e19\u0e40\u0e17\u0e34\u0e23\u0e4c\u0e19\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f")

    assert match.detected is True
    assert match.command_text == "\u0e40\u0e1b\u0e34\u0e14\u0e44\u0e1f"


def test_alternative_wake_word_is_supported() -> None:
    match = WakeWordVerifier(alternatives=("lantern",)).match("LANtern เปิดไฟ")

    assert match.detected is True
    assert match.matched_phrase == "lantern"


def test_wake_word_must_start_transcript() -> None:
    assert WakeWordVerifier().verify("เปิดไฟ แลนเทิร์น") is False


def test_normalization_handles_punctuation_and_zero_width_space() -> None:
    match = WakeWordVerifier().match("แลนเทิร์น\u200b, เปิดไฟ!")

    assert match.detected is True
    assert match.command_text == "เปิดไฟ"
