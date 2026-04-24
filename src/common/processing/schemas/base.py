from pydantic import BaseModel


class MLRequest(BaseModel):
    tag: str = ""


class MLResponse(BaseModel):
    is_error: bool = False
    error: str = ""
