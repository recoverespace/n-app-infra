from math import ceil
from typing import Any, Generic, TypeVar
from collections.abc import Sequence
from fastapi_pagination import Params, Page
from fastapi_pagination.bases import AbstractPage
from pydantic import Field
from pydantic import BaseModel

DataType = TypeVar("DataType")
T = TypeVar("T")


class PageBase(Page[T], Generic[T]):
    previous_page: int | None = Field(default=None, description="Page number of the previous page")
    next_page: int | None = Field(default=None, description="Page number of the next page")


class ResponseBase(BaseModel, Generic[T]):
    message: str = ""
    meta: dict | Any | None = {}
    data: T | None = None


class GetResponsePaginated(AbstractPage[T], Generic[T]):
    message: str = ""
    meta: dict | None = None
    data: PageBase[T]

    __params_type__ = Params  # Set params related to Page

    @classmethod
    def create(cls, *args, items: Sequence[T], params: Params, **kwargs) -> PageBase[T] | None:
        total = kwargs.get("total", 0)
        if params.size is not None and total is not None and params.size != 0:
            pages = ceil(total / params.size)
        else:
            pages = 0

        return cls(
            data=PageBase[T](
                items=items,
                page=params.page,
                size=params.size,
                total=total,
                pages=pages,
                next_page=params.page + 1 if params.page < pages else None,
                previous_page=params.page - 1 if params.page > 1 else None,
            )
        )


class GetResponseBase(ResponseBase[DataType], Generic[DataType]):
    message: str = "Data got correctly"


class PostResponseBase(ResponseBase[DataType], Generic[DataType]):
    message: str = "Data created correctly"


class PutResponseBase(ResponseBase[DataType], Generic[DataType]):
    message: str = "Data updated correctly"


class DeleteResponseBase(ResponseBase[DataType], Generic[DataType]):
    message: str = "Data deleted correctly"


def create_response(
    data: DataType,
    message: str | None = None,
    meta: dict | Any | None = None,
) -> (
    ResponseBase[DataType]
    | GetResponsePaginated[DataType]
    | GetResponseBase[DataType]
    | PutResponseBase[DataType]
    | DeleteResponseBase[DataType]
    | PostResponseBase[DataType]
):
    if isinstance(data, GetResponsePaginated):
        data.message = "Data paginated correctly" if message is None else message
        data.meta = meta or {}
        return data
    if message is None:
        return {"data": data, "meta": meta or {}}  # type: ignore
    return {"data": data, "message": message, "meta": meta}  # type: ignore
