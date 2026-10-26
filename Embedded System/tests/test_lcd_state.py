import unittest
from enum import Enum


class DisplayState(Enum):
    BOOTING = "BOOTING"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    COMMAND_ACCEPTED = "COMMAND_ACCEPTED"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    LIGHT_ON = "LIGHT_ON"
    LIGHT_OFF = "LIGHT_OFF"
    WIFI_DISCONNECTED = "WIFI_DISCONNECTED"
    BACKEND_ERROR = "BACKEND_ERROR"


MESSAGES = {
    DisplayState.BOOTING: ("LANTERN BOOTING", "STARTING"),
    DisplayState.IDLE: ("READY", "SAY TEE"),
    DisplayState.LISTENING: ("LISTENING", "WAITING SPEECH"),
    DisplayState.RECORDING: ("RECORDING", "CAPTURING"),
    DisplayState.PROCESSING: ("PROCESSING", "ASR + INTENT"),
    DisplayState.COMMAND_ACCEPTED: ("COMMAND OK", "ACCEPTED"),
    DisplayState.COMMAND_REJECTED: ("COMMAND NO", "REJECTED"),
    DisplayState.LIGHT_ON: ("LIGHT ON", "GPIO CMD SENT"),
    DisplayState.LIGHT_OFF: ("LIGHT OFF", "GPIO CMD SENT"),
    DisplayState.WIFI_DISCONNECTED: ("WIFI OFFLINE", "RECONNECTING"),
    DisplayState.BACKEND_ERROR: ("BACKEND ERROR", "CHECK SERVER"),
}


class MockLcd:
    def __init__(self, available: bool) -> None:
        self.available = available
        self.state = DisplayState.BOOTING
        self.lines = ("", "")
        self.refresh_count = 0

    def set_state(self, state: DisplayState, detail: str | None = None) -> None:
        if not self.available:
            return
        default_line1, default_line2 = MESSAGES[state]
        next_lines = (
            default_line1[:16],
            (detail or default_line2)[:16],
        )
        if next_lines == self.lines:
            return
        self.state = state
        self.lines = next_lines
        self.refresh_count += 1


class DisplayPriorityModel:
    """Host model for main.cpp's recording/Wi-Fi display priority."""

    def __init__(self) -> None:
        self.state = DisplayState.LISTENING
        self.holding_message = False

    def refresh(self, *, recording: bool, wifi_connected: bool) -> None:
        if self.holding_message:
            return
        if not wifi_connected:
            self.state = DisplayState.WIFI_DISCONNECTED
        elif recording:
            self.state = DisplayState.RECORDING
        else:
            self.state = DisplayState.LISTENING

    def utterance_completed(self) -> None:
        if not self.holding_message:
            self.state = DisplayState.PROCESSING


class LcdStateTests(unittest.TestCase):
    def test_initialization_and_unavailable_lcd(self) -> None:
        lcd = MockLcd(available=False)

        lcd.set_state(DisplayState.BOOTING)

        self.assertEqual(lcd.refresh_count, 0)
        self.assertEqual(lcd.state, DisplayState.BOOTING)

    def test_state_transitions_use_16_column_lines(self) -> None:
        lcd = MockLcd(available=True)

        for state in DisplayState:
            lcd.set_state(state)
            self.assertLessEqual(len(lcd.lines[0]), 16)
            self.assertLessEqual(len(lcd.lines[1]), 16)

        self.assertEqual(lcd.state, DisplayState.BACKEND_ERROR)

    def test_repeated_state_does_not_refresh(self) -> None:
        lcd = MockLcd(available=True)

        lcd.set_state(DisplayState.LISTENING)
        first_refreshes = lcd.refresh_count
        lcd.set_state(DisplayState.LISTENING)

        self.assertEqual(lcd.refresh_count, first_refreshes)

    def test_accepted_light_states_show_gpio_dispatch(self) -> None:
        lcd = MockLcd(available=True)

        lcd.set_state(DisplayState.LIGHT_ON)
        self.assertEqual(lcd.lines, ("LIGHT ON", "GPIO CMD SENT"))
        lcd.set_state(DisplayState.LIGHT_OFF)
        self.assertEqual(lcd.lines, ("LIGHT OFF", "GPIO CMD SENT"))

    def test_rejected_backend_and_network_states_are_distinct(self) -> None:
        lcd = MockLcd(available=True)

        lcd.set_state(DisplayState.COMMAND_REJECTED, "WAKE/INTENT NO")
        self.assertEqual(lcd.state, DisplayState.COMMAND_REJECTED)
        lcd.set_state(DisplayState.WIFI_DISCONNECTED)
        self.assertEqual(lcd.lines, ("WIFI OFFLINE", "RECONNECTING"))
        lcd.set_state(DisplayState.BACKEND_ERROR, "HTTP TIMEOUT")
        self.assertEqual(lcd.lines, ("BACKEND ERROR", "HTTP TIMEOUT"))

    def test_recording_has_priority_over_normal_listening_refresh(self) -> None:
        display = DisplayPriorityModel()

        display.refresh(recording=True, wifi_connected=True)
        self.assertEqual(display.state, DisplayState.RECORDING)

        # The audio segment remains active across subsequent frames.
        display.refresh(recording=True, wifi_connected=True)
        self.assertEqual(display.state, DisplayState.RECORDING)

        display.utterance_completed()
        self.assertEqual(display.state, DisplayState.PROCESSING)

    def test_wifi_offline_is_not_overwritten_until_reconnect(self) -> None:
        display = DisplayPriorityModel()

        display.refresh(recording=False, wifi_connected=False)
        self.assertEqual(display.state, DisplayState.WIFI_DISCONNECTED)
        display.refresh(recording=False, wifi_connected=False)
        self.assertEqual(display.state, DisplayState.WIFI_DISCONNECTED)

        display.refresh(recording=False, wifi_connected=True)
        self.assertEqual(display.state, DisplayState.LISTENING)

    def test_wifi_error_has_priority_over_recording_refresh(self) -> None:
        display = DisplayPriorityModel()

        display.refresh(recording=True, wifi_connected=False)

        self.assertEqual(display.state, DisplayState.WIFI_DISCONNECTED)

    def test_non_recording_audio_does_not_fake_recording_state(self) -> None:
        display = DisplayPriorityModel()

        display.refresh(recording=False, wifi_connected=True)
        self.assertEqual(display.state, DisplayState.LISTENING)

    def test_temporary_message_blocks_normal_refresh(self) -> None:
        display = DisplayPriorityModel()
        display.state = DisplayState.LIGHT_ON
        display.holding_message = True

        display.refresh(recording=False, wifi_connected=True)

        self.assertEqual(display.state, DisplayState.LIGHT_ON)


if __name__ == "__main__":
    unittest.main()
