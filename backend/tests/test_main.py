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


def test_non_wav_is_rejected_before_asr() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post(
        "/v1/utterances/transcribe",
        files={"audio": ("utterance.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 400
