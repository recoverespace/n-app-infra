from typing import Generic, TypeVar
from uuid import UUID
from uuid_utils import uuid7
from sqlmodel import SQLModel, Field, JSON, TypeDecorator, DateTime
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from pydantic import TypeAdapter
from pydantic._internal._model_construction import ModelMetaclass
import json

PydanticJSONType = JSON

T = TypeVar("T", bound=SQLModel)


def pydantic_column_type(pydantic_type):
    class PydanticJSONType(TypeDecorator, Generic[T]):
        impl = JSON()

        def __init__(
            self,
            json_encoder=json,
        ):
            self.json_encoder = json_encoder
            super().__init__()

        def bind_processor(self, dialect):  # type: ignore
            impl_processor = self.impl.bind_processor(dialect)  # type: ignore
            dumps = self.json_encoder.dumps
            if impl_processor:

                def process(value: T):  # type: ignore
                    if value is not None:
                        if isinstance(pydantic_type, ModelMetaclass):
                            # This allows to assign non-InDB models and if they're
                            # compatible, they're directly parsed into the InDB
                            # representation, thus hiding the implementation in the
                            # background. However, the InDB model will still be returned
                            value_to_dump = pydantic_type.model_validate(value)  # type: ignore
                        else:
                            value_to_dump = value
                        value = jsonable_encoder(value_to_dump)
                    return impl_processor(value)

            else:

                def process(value):
                    if isinstance(pydantic_type, ModelMetaclass):
                        # This allows to assign non-InDB models and if they're
                        # compatible, they're directly parsed into the InDB
                        # representation, thus hiding the implementation in the
                        # background. However, the InDB model will still be returned
                        value_to_dump = pydantic_type.model_validate(value)  # type: ignore
                    else:
                        value_to_dump = value
                    value = dumps(jsonable_encoder(value_to_dump))
                    return value

            return process

        def result_processor(self, dialect, coltype) -> T:  # type: ignore
            impl_processor = self.impl.result_processor(dialect, coltype)  # type: ignore
            if impl_processor:

                def process(value):
                    value = impl_processor(value)
                    if value is None:
                        return None

                    data = value
                    # Explicitly use the generic directly, not type(T)
                    full_obj = TypeAdapter(pydantic_type).validate_python(data)
                    return full_obj

            else:

                def process(value):
                    if value is None:
                        return None

                    # Explicitly use the generic directly, not type(T)
                    if isinstance(value, str):
                         full_obj = TypeAdapter(pydantic_type).validate_json(value)
                    else:
                        full_obj = TypeAdapter(pydantic_type).validate_python(value)
                    return full_obj

            return process  # type: ignore

        def compare_values(self, x, y):
            return x == y

    return PydanticJSONType


class BaseIDModel(SQLModel):
    id: int | None = Field(default=None, primary_key=True)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_type=DateTime(timezone=True),  # type: ignore
        sa_column_kwargs={"onupdate": datetime.now},
    )
    created_at: datetime = Field(default_factory=datetime.now, sa_type=DateTime(timezone=True))  # type: ignore


class BaseUUIDModel(SQLModel):
    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True,
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_type=DateTime(timezone=True),  # type: ignore
        sa_column_kwargs={"onupdate": datetime.now},
    )
    created_at: datetime = Field(default_factory=datetime.now, sa_type=DateTime(timezone=True))  # type: ignore


def make_updater_cls(self) -> SQLModel:
    """From a base model, make and return an update model. As described in
    https://sqlmodel.tiangolo.com/tutorial/fastapi/update/#heroupdate-model, the update model
    is the same as the base model, but with all fields annotated as ``Optional`` and all field
    defaults set to ``None``.
    :param base: The base model. Note that unlike in ``make_creator``, this is not the base for
    inheritance (all updaters inherit directly from ``SQLModel``) but rather is used to derive
    the output class name, attributes, and type annotations.
    """

    cls_name = self.base.__name__.replace("Base", "") + "Update"
    sig = self.base.__signature__
    params = list(sig.parameters)
    # Pulling type via `__signature__` rather than `__annotation__` because
    # this accessor drops the `typing.Union[...]` wrapper for optional fields
    annotations = {p: sig.parameters[p].annotation | None for p in params}
    defaults = {p: None for p in params}
    attrs = {**defaults, "__annotations__": annotations}
    return type(cls_name, (SQLModel,), attrs)
