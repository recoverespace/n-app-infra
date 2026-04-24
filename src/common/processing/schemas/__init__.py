from .base import MLRequest, MLResponse
from .tts import TTSModel, TTSRequest, TTSResponse
from .llm import LLMModel, LLMRequest, LLMResponse
from .audio import ASRModel, ASRRequest, ASRResponse
from .photo_caption import PhotoCaptionRequest, PhotoCaptionResponse
from .opensearch import (
    OpenSearchRequest,
    OpenSearchResponse,
    OpenSearchDocument,
)
from .pubmed import PubMedRequest, PubMedResponse, PubMedDocument
from .dialog import DialogMessage, DialogResponseMessage, DialogIntentRequest, DialogIntentResponse, DialogRunIntentRequest, DialogTriggerMessage
from .image_generation import ImageGenerationRequest, ImageGenerationResponse

__all__ = [
    "MLRequest",
    "MLResponse",
    "TTSModel",
    "TTSRequest",
    "TTSResponse",
    "LLMModel",
    "LLMRequest",
    "LLMResponse",
    "ASRModel",
    "ASRRequest",
    "ASRResponse",
    "PhotoCaptionRequest",
    "PhotoCaptionResponse",
    "OpenSearchRequest",
    "OpenSearchResponse",
    "OpenSearchDocument",
    "PubMedRequest",
    "PubMedResponse",
    "PubMedDocument",
    "DialogMessage",
    "DialogResponseMessage",
    "DialogIntentRequest",
    "DialogIntentResponse",
    "DialogTriggerMessage",
    "DialogRunIntentRequest",
    "ImageGenerationRequest",
    "ImageGenerationResponse",
]

AnyMLRequest = TTSRequest | LLMRequest | ASRRequest | PhotoCaptionRequest | OpenSearchRequest | PubMedRequest

AnyMLResponse = (
    TTSResponse | LLMResponse | ASRResponse | PhotoCaptionResponse | OpenSearchResponse | PubMedResponse
)
