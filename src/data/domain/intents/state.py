from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field
from common.otel import get_logger
from data.domain.chat_messages.schemas.message import UserOption
from data.domain.config.schemas import default_llm_models

logger = get_logger(__name__)


class ProactivityState(StrEnum):
    START = "start"
    PROGRESS = "progress"
    END = "end"


class ProactivityContext(BaseModel):
    id: str
    kind: str
    state: ProactivityState = ProactivityState.START
    steps: list[str] = Field(default_factory=list)
    current_step: str | None = None
    on_finish: str | None = None
    on_cancel: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    def advance(self, data: dict[str, Any] | None = None):
        # Find next step
        logger.info(f"Advancing proactivity context {self.id}")
        if not self.current_step:
            self.current_step = self.steps[0]
        current_step_index = self.steps.index(self.current_step)
        next_step_index = current_step_index + 1
        new_data = (self.data or {}) | data if data else self.data
        if next_step_index >= len(self.steps):
            logger.info(f"Finishing proactivity context {self.id} with step {self.on_finish}")
            self.state = ProactivityState.END
            self.current_step = self.on_finish
            self.data = new_data
            return
        self.current_step = self.steps[next_step_index]
        self.state = ProactivityState.PROGRESS
        self.data = new_data
        logger.info(f"Advancing proactivity context {self.id} to step {self.current_step}")

    def cancel(self, data: dict[str, Any] | None = None):
        new_data = (self.data or {}) | data if data else self.data
        logger.info(f"Cancelling proactivity context {self.id}")
        self.state = ProactivityState.END
        self.data = new_data


class PendingHandler(BaseModel):
    intent: str
    method: str


class ChatState(BaseModel):
    user_id: int | None = None
    goals: list[str] = Field(default_factory=list)
    llm_models: dict[str, str] = Field(default_factory=default_llm_models)
    default_intent: str | None = None
    previous_intent: str | None = None
    available_intents: list[str] = Field(default=[])
    routable_intents: list[str] = Field(default=[])
    pending_handler: PendingHandler | None = None
    proactivity: ProactivityContext | None = None
    options: list[UserOption] | None = None
    preprocessors: list[str] = Field(default_factory=list)
    postprocessors: list[str] = Field(default_factory=list)
    response_postprocessors: list[str] = Field(default_factory=list)

    @classmethod
    def default(cls, user_id: int) -> Self:
        return cls(
            user_id=user_id,
            goals=[],
            default_intent="ChatIntent",
            previous_intent=None,
            available_intents=[
                "Affirmation",
                "BabyBond",
                "ChatIntent",
                "DailySummary",
                "AppFeatureFAQIntent",
                "LengoldCheckin",
                "Lifestyle",
                "MindfulAudio",
                "MindfulPhotography",
                "ProfileIntent",
                "PersonalHistoryQAIntent",
                "SymptomsCheckin",
            ],
            routable_intents=[
                "Affirmation",
                "BabyBond",
                "ChatIntent",
                "DailySummary",
                "AppFeatureFAQIntent",
                "LengoldCheckin",
                "Lifestyle",
                "MindfulAudio",
                "MindfulPhotography",
                "ProfileIntent",
                "PersonalHistoryQAIntent",
                "SymptomsCheckin",
            ],
            pending_handler=None,
            proactivity=None,
            options=None,
            preprocessors=["PhotoCaptioning", "AudioProcessing", "Router"],
            postprocessors=["GoalCompletion"],
            response_postprocessors=[],
        )
