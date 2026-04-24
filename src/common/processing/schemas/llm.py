from enum import StrEnum
from typing import Any

from pydantic import Field
from common.processing.schemas.base import MLRequest, MLResponse


class LLMModel(StrEnum):
    GPT35 = "gpt-3.5-turbo"
    GPT4 = "gpt-4"
    GPT4o = "gpt-4o"
    LLAMA3 = "llama-3"


class LLMRequest(MLRequest):
    model: LLMModel = LLMModel.GPT35
    temperature: float = 0.7
    prompt: str = ""
    system: str = ""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    n: int = 1
    stop: str = ""
    tools: list[dict[str, Any]] = Field(default_factory=list)
    force_tool: bool = False
    params: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(MLResponse):
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    choices: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
