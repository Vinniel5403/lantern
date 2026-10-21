from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.schemas import UtteranceResponse
from app.services.asr import ASRProvider, create_asr_provider
from app.services.intents import IntentDetector
from app.services.wake_word import WakeWordVerifier


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    application = FastAPI(title="Lantern", version="0.1.0")
    application.state.settings = runtime_settings
    application.state.asr_provider = create_asr_provider(runtime_settings)
    application.state.wake_word_verifier = WakeWordVerifier(runtime_settings.wake_phrase)
    application.state.intent_detector = IntentDetector()

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/v1/utterances/transcribe",
        response_model=UtteranceResponse,
        status_code=status.HTTP_200_OK,
    )
    async def transcribe_utterance(
        audio: UploadFile = File(...),
        provider: ASRProvider = Depends(
            lambda: application.state.asr_provider
        ),
    ) -> UtteranceResponse:
        audio_bytes = await audio.read(runtime_settings.max_audio_bytes + 1)
        if len(audio_bytes) > runtime_settings.max_audio_bytes:
            raise HTTPException(status_code=413, detail="audio file is too large")
        if not audio_bytes.startswith(b"RIFF") or audio_bytes[8:12] != b"WAVE":
            raise HTTPException(status_code=400, detail="expected a RIFF/WAVE file")

        try:
            transcript = await provider.transcribe(
                audio_bytes,
                filename=audio.filename or "utterance.wav",
                content_type=audio.content_type or "audio/wav",
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        wake_word_detected = application.state.wake_word_verifier.verify(transcript.text)
        intent = (
            application.state.intent_detector.detect(transcript.text)
            if wake_word_detected
            else application.state.intent_detector.detect("")
        )
        return UtteranceResponse(
            transcript=transcript,
            wake_word_detected=wake_word_detected,
            intent=intent,
        )

    return application


app = create_app()
