from enum import StrEnum
from common.processing.schemas.base import MLRequest, MLResponse


class ASRModel(StrEnum):
    WHISPER = "whisper-1"


class ASRRequest(MLRequest):
    model: ASRModel = ASRModel.WHISPER
    url: str = ""


class ASRResponse(MLResponse):
    content: str = ""
