from enum import StrEnum
from typing import Any
from common.processing.schemas.base import MLRequest, MLResponse


class TTSModel(StrEnum):
    MULTILINGUAL_V2 = "eleven_multilingual_v2"


class TTSRequest(MLRequest):
    model: TTSModel = TTSModel.MULTILINGUAL_V2
    text: str = ""
    context: str = ""


class TTSResponse(MLResponse):
    audio: Any
    text: str
    context: str = ""
