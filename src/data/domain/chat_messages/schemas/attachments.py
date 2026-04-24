from enum import StrEnum
from typing import Any, Literal, TypeVar
from pydantic import BaseModel
from sqlmodel import Field
from uuid import uuid4

from data.domain.static_files.models import StaticFile
from data.domain.static_files.schemas import StaticContentTypes


class AttachmentType(StrEnum):
    audio = "audio"
    voice = "voice"
    file = "file"
    image = "image"
    external_link = "external-link"
    legacy_library = "legacy-library"
    baby_size_tracker = "baby-size-tracker"
    unsupported = "unsupported"
    video = "video"
    emotions = "emotions"
    emotion = "emotion"
    emotion_slider = "emotion-slider"
    symptoms = "symptoms"
    symptoms_checkin = "symptoms_checkin"
    energy_result = "energy-result"
    energy_checkin = "energy-checkin"
    proactivity_trigger = "proactivity-trigger"
    eat_test = "eat-test"


class ProactivityKind(StrEnum):
    BabyBond = "baby_bond"
    LifestyleCheckin = "lifestyle_checkin"
    MindfulPhotography = "mindful_photography"
    MindfulnessAudio = "mindfulness_audio"
    NeurobalanceCheckin = "neurobalance_checkin"
    SymptomsCheckin = "symptoms_checkin"
    WomensQuestions = "womens_questions"


class BaseAttachment(BaseModel):
    attachment_id: str = Field(default_factory=lambda: str(uuid4()))


class EatTestAttachment(BaseAttachment):
    type: Literal[AttachmentType.eat_test] = AttachmentType.eat_test


class FileAttachment(BaseAttachment):
    url: str
    type: Literal[AttachmentType.file] = AttachmentType.file


class AudioAttachment(BaseAttachment):
    url: str
    type: Literal[AttachmentType.audio] = AttachmentType.audio
    transcription: str | None = None


class VoiceAttachment(BaseAttachment):
    url: str
    type: Literal[AttachmentType.voice] = AttachmentType.voice
    duration: int = 0
    metering: list[float] = Field(default_factory=list)
    transcription: str | None = None


class VideoAttachment(BaseAttachment):
    url: str
    type: Literal[AttachmentType.video] = AttachmentType.video


class LegacyLibraryAttachment(BaseAttachment):
    id: int
    type: Literal[AttachmentType.legacy_library] = AttachmentType.legacy_library


class BabySizeTrackerAttachment(BaseAttachment):
    week: int = 0
    type: Literal[AttachmentType.baby_size_tracker] = AttachmentType.baby_size_tracker


class ExternalLinkAttachment(BaseAttachment):
    url: str
    id: int
    type: Literal[AttachmentType.external_link] = AttachmentType.external_link


class EmotionAttachment(BaseAttachment):
    emotion: str
    max_strength: int
    min_strength: int
    strength: int
    type: Literal[AttachmentType.emotion] = AttachmentType.emotion
    transcription: str | None = None


class EmotionsAttachment(BaseAttachment):
    emotions: list[dict[str, str]] = []
    type: Literal[AttachmentType.symptoms] = AttachmentType.symptoms


class EmotionSliderAttachment(BaseAttachment):
    emotion: str
    max_strength: int
    min_strength: int
    strength: int | None = None
    type: Literal[AttachmentType.emotion_slider] = AttachmentType.emotion_slider


class UnsupportedAttachment(BaseAttachment):
    type: Literal[AttachmentType.unsupported] = AttachmentType.unsupported


class ImageAttachment(BaseAttachment):
    url: str
    size: dict[str, int] | None = None
    type: Literal[AttachmentType.image] = AttachmentType.image
    transcription: str | None = None


class SymptomsAttachment(BaseAttachment):
    symptoms: list[dict[str, str]] = []
    type: Literal[AttachmentType.symptoms] = AttachmentType.symptoms
    transcription: str | None = None


class SymptomsCheckinAttachment(BaseAttachment):
    answers: list[dict[str, str]] = []
    type: Literal[AttachmentType.symptoms_checkin] = AttachmentType.symptoms_checkin
    transcription: str | None = None


class EnergyResultAttachment(BaseAttachment):
    value: int
    type: Literal[AttachmentType.energy_result] = AttachmentType.energy_result


class EnergyCheckinAttachment(BaseAttachment):
    answers: list[dict[str, str]] = []
    type: Literal[AttachmentType.energy_checkin] = AttachmentType.energy_checkin
    transcription: str | None = None


class ProactivityTriggerAttachment(BaseAttachment):
    kind: ProactivityKind
    params: dict[str, Any] = {}
    type: Literal[AttachmentType.proactivity_trigger]


AnyAttachment = TypeVar(
    "AnyAttachment",
    AudioAttachment,
    VoiceAttachment,
    ExternalLinkAttachment,
    FileAttachment,
    ImageAttachment,
    LegacyLibraryAttachment,
    UnsupportedAttachment,
    VideoAttachment,
    BabySizeTrackerAttachment,
    EmotionAttachment,
    EmotionSliderAttachment,
    SymptomsAttachment,
    SymptomsCheckinAttachment,
    EnergyResultAttachment,
    ProactivityTriggerAttachment,
    EatTestAttachment,
)

Attachment = (
    AudioAttachment
    | VoiceAttachment
    | ExternalLinkAttachment
    | FileAttachment
    | ImageAttachment
    | LegacyLibraryAttachment
    | UnsupportedAttachment
    | VideoAttachment
    | BabySizeTrackerAttachment
    | EmotionAttachment
    | EmotionSliderAttachment
    | SymptomsAttachment
    | EnergyResultAttachment
    | ProactivityTriggerAttachment
    | EatTestAttachment
)


def convert_from_file(file: StaticFile, chat_id: int) -> Attachment:
    if file.content_type == StaticContentTypes.audio:
        return AudioAttachment(url=file.get_url(chat_id), transcription=file.extra.get("transcription"))
    elif file.content_type == StaticContentTypes.voice:
        return VoiceAttachment(
            url=file.get_url(chat_id),
            transcription=file.extra.get("transcription"),
            duration=file.extra.get("duration", 10),
            metering=file.extra.get("metering", []),
        )
    elif file.content_type == StaticContentTypes.image:
        return ImageAttachment(
            url=file.get_url(chat_id),
            transcription=file.extra.get("transcription"),
            size=file.extra.get("size", {"width": 100, "height": 100}),
        )
    else:
        return UnsupportedAttachment()
