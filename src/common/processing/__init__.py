from uuid import uuid4
from faststream.redis import StreamSub

from common.processing.streams import StreamType


def stream_sub(stream: StreamType, group: str) -> StreamSub:
    consumer_id = str(uuid4())
    return StreamSub(stream=stream.value, group=group, consumer=consumer_id)
