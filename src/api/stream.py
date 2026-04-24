from faststream import FastStream

from api.broker import broker
from api.dialog_processors import process_dialog_message
from api.settings import settings
from common.otel import get_logger, init_telemetry
from common.processing import stream_sub
from common.processing.schemas.dialog import DialogActionMessage, DialogTriggerMessage
from common.processing.streams import StreamType

init_telemetry(f"{settings.SERVICE_PREFIX}-api-stream")
logger = get_logger(__name__)

app = FastStream(broker)


@broker.subscriber(stream=stream_sub(stream=StreamType.DIALOG, group="dialog_action"))
async def dialog_action_processor(req: DialogActionMessage | DialogTriggerMessage):
    await process_dialog_message(req)
