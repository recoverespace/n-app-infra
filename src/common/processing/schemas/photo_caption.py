from common.processing.schemas.base import MLRequest, MLResponse


class PhotoCaptionRequest(MLRequest):
    url: str


class PhotoCaptionResponse(MLResponse):
    prediction: str = ""
