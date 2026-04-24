from datetime import datetime
from typing import Any
from sqlmodel import SQLModel, Field, Column, DateTime

from data.lib.model import pydantic_column_type


def default_override():
    return {
        "add": [],
        "remove": [],
        "override": [],
    }


def default_llm_models():
    return {
        "common": "gpt-3.5-turbo",
        "chat": "gpt-3.5-turbo",
        "advanced": "gpt-4o",
        "fallback": "gpt-3.5-turbo",
    }


class ConfigOverrides(SQLModel):
    preprocessors: dict[str, list[str]] = Field(default_factory=default_override)
    postprocessors: dict[str, list[str]] = Field(default_factory=default_override)
    response_postprocessors: dict[str, list[str]] = Field(default_factory=default_override)
    available_intents: dict[str, list[str]] = Field(default_factory=default_override)
    routable_intents: dict[str, list[str]] = Field(default_factory=default_override)
    llm_models: dict[str, Any] = Field(default_factory=default_llm_models)

    def get_config(self, prev_config: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for k in [
            "preprocessors",
            "postprocessors",
            "response_postprocessors",
            "available_intents",
            "routable_intents",
        ]:
            overrided = getattr(self, k).get("override", [])
            if overrided:
                result[k] = overrided
            else:
                result[k] = prev_config[k] + getattr(self, k).get("add", [])
                result[k] = [v for v in result[k] if v not in getattr(self, k).get("remove", [])]
        result["llm_models"] = prev_config["llm_models"] | self.llm_models
        return result


class ConfigBase(SQLModel):
    priority: int = 0
    enabled: bool = False
    segment: str | None = None
    start_date: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    end_date: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    priority: int = 0
    overrides: ConfigOverrides = Field(
        default_factory=ConfigOverrides, sa_column=Column(pydantic_column_type(ConfigOverrides))
    )


class ConfigUpdate(ConfigBase): ...


class ConfigCreate(ConfigBase): ...


class ConfigRead(ConfigBase):
    id: int
