from common.processing.schemas.base import MLRequest, MLResponse
from common.settings import settings


class ImageGenerationRequest(MLRequest):
    type: str
    target_key: str
    bg_dir: str
    text: str = ""
    font_file: str = "./fonts/mf846615.otf"
    target_bucket: str = settings.GCS_BUCKET


class ImageGenerationResponse(MLResponse):
    size: dict = {}
