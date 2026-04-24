from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field


class Suggestion(BaseModel):
    label: str
    value: str


class SuggestionType(StrEnum):
    single = "single"
    multi = "multi"


class SuggestionKind(StrEnum):
    # TODO: Too specific name, need to change to something more generic
    symptoms = "symptoms"
    suggestion = "suggestion"


class Suggestions(BaseModel):
    values: list[Suggestion] = Field(default_factory=list)
    selectionType: SuggestionType = SuggestionType.single
    kind: SuggestionKind = SuggestionKind.suggestion

    model_config = ConfigDict(from_attributes=True)
