from enum import StrEnum

from faststream.redis import RedisBroker
from faststream.types import DecodedMessage, SendableMessage

from common.processing.broker import get_broker
from common.processing.schemas import (
    ASRRequest,
    ASRResponse,
    DialogMessage,
    DialogResponseMessage,
    DialogIntentRequest,
    DialogIntentResponse,
    DialogRunIntentRequest,
    DialogTriggerMessage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    LLMRequest,
    LLMResponse,
    OpenSearchRequest,
    OpenSearchResponse,
    PhotoCaptionRequest,
    PhotoCaptionResponse,
    PubMedRequest,
    PubMedResponse,
    TTSRequest,
    TTSResponse,
)
from common.processing.schemas.dialog import DialogActionMessage


class StreamType(StrEnum):
    CHAT_PROCESSING = "chat_processing"
    IMAGE_PROCESSING = "image_processing"
    OPENAI_PROCESSING = "openai_processing"
    OPENAI_AUDIO_PROCESSING = "openai_audio_processing"
    ELEVENLABS_PROCESSING = "elevenlabs_processing"
    OPENSEARCH_QUERY = "opensearch_query"
    PUBMED_QUERY = "pubmed_query"
    ML_RESPONSE = "ml_response"
    DIALOG = "dialog"
    DIALOG_RESPONSE = "dialog_response"
    DIALOG_ACTION = "dialog_action"
    DIALOG_INTENT = "dialog_intent" # TODO: remova after migration
    DIALOG_RUN_INTENT = "dialog_run_intent"
    IMAGE_GENERATION = "image_generation"


DEFAULT_TIMEOUT = 12


async def test_broker_connection() -> bool:
    broker = await get_broker()
    try:
        await broker.ping()
        return True
    except Exception:
        return False

async def new_dialog_message(data: DialogMessage):
    broker = await get_broker()
    await broker.publish(data, stream=StreamType.DIALOG.value)


async def dialog_trigger(data: DialogTriggerMessage):
    broker = await get_broker()
    await broker.publish(data, stream=StreamType.DIALOG.value)

async def dialog_response_message(data: DialogResponseMessage):
    broker = await get_broker()
    await broker.publish(data, stream=StreamType.DIALOG_RESPONSE.value)


async def dialog_action_message(data: DialogActionMessage):
    broker = await get_broker()
    await broker.publish(data, stream=StreamType.DIALOG_ACTION.value)


async def _call(
    stream: StreamType, data: SendableMessage, broker: RedisBroker, timeout: int = DEFAULT_TIMEOUT
) -> DecodedMessage:
    message = await broker.publish(data, stream=stream, rpc=True, rpc_timeout=timeout, raise_timeout=True)
    return message


async def run_dialog_intent(data: DialogIntentRequest) -> DialogIntentResponse:
    broker = await get_broker()
    message = await _call(StreamType.DIALOG_INTENT, data, broker, timeout=2 * DEFAULT_TIMEOUT)
    return DialogIntentResponse.model_validate(message)


async def dialog_run_intent(data: DialogRunIntentRequest) -> DialogIntentResponse:
    broker = await get_broker()
    message = await _call(StreamType.DIALOG_RUN_INTENT, data, broker, timeout=2 * DEFAULT_TIMEOUT)
    return DialogIntentResponse.model_validate(message)


async def llm_call(data: LLMRequest, timeout: int = DEFAULT_TIMEOUT) -> LLMResponse:
    broker = await get_broker()
    message = await _call(StreamType.OPENAI_PROCESSING, data, broker, timeout)
    return LLMResponse.model_validate(message)


async def openai_audio_call(data: ASRRequest, timeout: int = DEFAULT_TIMEOUT) -> ASRResponse:
    broker = await get_broker()
    message = await _call(StreamType.OPENAI_PROCESSING, data, broker, timeout)
    return ASRResponse.model_validate(message)


async def elevenlabs_call(data: TTSRequest, timeout: int = DEFAULT_TIMEOUT) -> TTSResponse:
    broker = await get_broker()
    message = await _call(StreamType.ELEVENLABS_PROCESSING, data, broker, timeout)
    return TTSResponse.model_validate(message)


async def opensearch_query(data: OpenSearchRequest, timeout: int = DEFAULT_TIMEOUT) -> OpenSearchResponse:
    broker = await get_broker()
    message = await _call(StreamType.OPENSEARCH_QUERY, data, broker, timeout)
    return OpenSearchResponse.model_validate(message)


async def pubmed_query(data: PubMedRequest, timeout: int = DEFAULT_TIMEOUT) -> PubMedResponse:
    broker = await get_broker()
    message = await _call(StreamType.PUBMED_QUERY, data, broker, timeout)
    return PubMedResponse.model_validate(message)


async def photo_captioning(data: PhotoCaptionRequest, timeout: int = DEFAULT_TIMEOUT) -> PhotoCaptionResponse:
    broker = await get_broker()
    message = await _call(StreamType.IMAGE_PROCESSING, data, broker, timeout)
    return PhotoCaptionResponse.model_validate(message)


async def image_generation(
    data: ImageGenerationRequest, timeout: int = DEFAULT_TIMEOUT
) -> ImageGenerationResponse:
    broker = await get_broker()
    message = await _call(StreamType.IMAGE_GENERATION, data, broker, timeout)
    return ImageGenerationResponse.model_validate(message)
