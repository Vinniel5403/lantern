import logging

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.asr import MockASRProvider


def wav_fixture() -> bytes:
    return b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + b"phase-0-audio"


def test_health() -> None:
    client = TestClient(create_app(Settings()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_transcribe_uses_mock_asr_and_allowlisted_intent() -> None:
    application = create_app(Settings(wake_phrase="lantern"))
    application.state.asr_provider = MockASRProvider("Lantern เปิดไฟ")
    client = TestClient(application)

    response = client.post(
        "/v1/utterances/transcribe",
        files={"audio": ("utterance.wav", wav_fixture(), "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json()["wake_word_detected"] is True
    assert response.json()["intent"]["name"] == "LIGHT_ON"


def test_transcribe_logs_recognized_text(caplog) -> None:
    application = create_app(Settings())
    application.state.asr_provider = MockASRProvider("ทดสอบเสียง")
    client = TestClient(application)
    caplog.set_level(logging.INFO, logger="lantern.asr")

    response = client.post(
        "/v1/utterances/transcribe",
        files={"audio": ("utterance.wav", wav_fixture(), "audio/wav")},
    )

    assert response.status_code == 200
    assert "ทดสอบเสียง" in caplog.text


def test_non_wav_is_rejected_before_asr() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post(
        "/v1/utterances/transcribe",
        files={"audio": ("utterance.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 400


def test_uploaded_wav_can_be_saved_for_debugging(tmp_path) -> None:
    application = create_app(
        Settings(save_uploaded_audio=True, audio_save_dir=str(tmp_path))
    )
    application.state.asr_provider = MockASRProvider("ทดสอบเสียง")
    client = TestClient(application)

    response = client.post(
        "/v1/utterances/transcribe",
        files={"audio": ("utterance.wav", wav_fixture(), "audio/wav")},
    )

    assert response.status_code == 200
    saved_files = list(tmp_path.glob("utterance-*.wav"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == wav_fixture()
