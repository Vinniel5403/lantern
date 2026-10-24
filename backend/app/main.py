import logging
import re

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status

from app.audio import AudioFormatError, validate_wav
from app.audio_storage import save_wav
from app.config import Settings, get_settings
from app.schemas import IntentDecision, UtteranceResponse
from app.services.asr import ASRProvider, create_asr_provider
from app.services.deduplication import DuplicateSegmentGuard
from app.services.intents import IntentDetector
from app.services.replay_cache import RequestReplayCache
from app.services.wake_word import WakeWordVerifier


logger = logging.getLogger("lantern.asr")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _csv_values(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    application = FastAPI(title="Lantern", version="0.1.0")
    application.state.settings = runtime_settings
    application.state.asr_provider = create_asr_provider(runtime_settings)
    application.state.wake_word_verifier = WakeWordVerifier(
        runtime_settings.wake_phrase,
        _csv_values(runtime_settings.wake_word_alternatives),
    )
    application.state.intent_detector = IntentDetector()
    application.state.duplicate_guard = DuplicateSegmentGuard(
        runtime_settings.duplicate_window_s,
        runtime_settings.duplicate_cache_size,
    )
    application.state.request_replay_cache = RequestReplayCache(
        runtime_settings.request_replay_window_s,
        runtime_settings.request_replay_cache_size,
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/v1/utterances/transcribe",
        response_model=UtteranceResponse,
        status_code=status.HTTP_200_OK,
    )
    async def transcribe_utterance(
        request: Request,
        audio: UploadFile = File(...),
        provider: ASRProvider = Depends(
            lambda: application.state.asr_provider
        ),
    ) -> UtteranceResponse:
        request_id = request.headers.get("X-Lantern-Request-ID")
        if request_id is not None and not _REQUEST_ID_PATTERN.fullmatch(request_id):
            raise HTTPException(status_code=400, detail="invalid request ID")

        audio_bytes = await audio.read(runtime_settings.max_audio_bytes + 1)
        if len(audio_bytes) > runtime_settings.max_audio_bytes:
            raise HTTPException(status_code=413, detail="audio file is too large")
        try:
            validate_wav(audio_bytes)
        except AudioFormatError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if request_id:
            cached_response = application.state.request_replay_cache.get(request_id)
            if cached_response is not None:
                logger.info("execution_decision replayed_request=true request_id=%s", request_id)
                return cached_response.model_copy(
                    update={"replayed_request": True, "request_id": request_id}
                )

        if not application.state.duplicate_guard.reserve(audio_bytes):
            logger.info("execution_decision duplicate=true accepted=false")
            return UtteranceResponse(
                transcript={"text": "", "provider": "duplicate_guard"},
                wake_word_detected=False,
                duplicate_segment=True,
                request_id=request_id,
                intent={
                    "name": "IGNORE",
                    "accepted": False,
                    "reason": "duplicate audio segment",
                },
            )

        if runtime_settings.save_uploaded_audio:
            try:
                saved_path = save_wav(audio_bytes, runtime_settings.audio_save_dir)
            except OSError as exc:
                application.state.duplicate_guard.release(audio_bytes)
                logger.exception("could not save uploaded WAV")
                raise HTTPException(
                    status_code=500,
                    detail="could not save uploaded audio",
                ) from exc
            logger.info("saved uploaded WAV path=%s", saved_path)

        try:
            transcript = await provider.transcribe(
                audio_bytes,
                filename=audio.filename or "utterance.wav",
                content_type=audio.content_type or "audio/wav",
            )
        except RuntimeError as exc:
            application.state.duplicate_guard.release(audio_bytes)
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        logger.info(
            "recognized text provider=%s text=%r",
            transcript.provider,
            transcript.text,
        )
        wake_match = application.state.wake_word_verifier.match(transcript.text)
        logger.info(
            "wake_word_detection detected=%s matched_phrase=%r",
            wake_match.detected,
            wake_match.matched_phrase,
        )
        if runtime_settings.require_wake_word:
            command_text = wake_match.command_text if wake_match.detected else ""
        else:
            # Keep wake matching active for observability while allowing clear
            # commands from the full transcript during integration testing.
            command_text = (
                wake_match.command_text if wake_match.detected else transcript.text
            )

        if wake_match.detected or not runtime_settings.require_wake_word:
            intent = application.state.intent_detector.detect(command_text)
        else:
            intent = IntentDecision(
                name="IGNORE",
                accepted=False,
                reason="wake word missing",
            )
        logger.info(
            "intent_detection name=%s accepted=%s reason=%s",
            intent.name,
            intent.accepted,
            intent.reason,
        )
        logger.info(
            "execution_decision duplicate=false wake_word_detected=%s "
            "matched_wake_word=%r require_wake_word=%s intent=%s accepted=%s reason=%s",
            wake_match.detected,
            wake_match.matched_phrase,
            runtime_settings.require_wake_word,
            intent.name,
            intent.accepted,
            intent.reason,
        )
        result = UtteranceResponse(
            transcript=transcript,
            wake_word_detected=wake_match.detected,
            matched_wake_word=wake_match.matched_phrase,
            request_id=request_id,
            intent=intent,
        )
        if request_id:
            application.state.request_replay_cache.put(request_id, result)
        return result

    return application


app = create_app()
