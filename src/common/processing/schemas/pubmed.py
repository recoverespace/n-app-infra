from pydantic import BaseModel, Field
from common.processing.schemas.base import MLRequest, MLResponse


class PubMedRequest(MLRequest):
    query: str
    k: int = 3


class PubMedDocument(BaseModel):
    uid: int
    title: str
    content: str
    published: str
    copyright: str


class PubMedResponse(MLResponse):
    documents: list[PubMedDocument] = Field(default_factory=list)
