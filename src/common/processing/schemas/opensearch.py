from typing import Any
from pydantic import BaseModel, Field
from common.processing.schemas.base import MLRequest, MLResponse


class OpenSearchRequest(MLRequest):
    index: str
    query: str
    k: int = 3
    filters: dict[str, str] | None = None
    seen_items: list[int] | None = None
    stop_words: list[str] | None = None


class OpenSearchDocument(BaseModel):
    key: int
    content: str
    metadata: dict[Any, Any]
    score: float


class OpenSearchResponse(MLResponse):
    documents: list[OpenSearchDocument] = Field(default_factory=list)
