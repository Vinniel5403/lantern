from pydantic import BaseModel, ConfigDict, Field


class Transcript(BaseModel):
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    provider: str


class IntentDecision(BaseModel):
    name: str = "NO_ACTION"
    parameters: dict[str, str] = Field(default_factory=dict)
    accepted: bool = False
    reason: str


class UtteranceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript: Transcript
    wake_word_detected: bool
    intent: IntentDecision
