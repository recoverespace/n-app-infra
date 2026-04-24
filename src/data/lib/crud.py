from collections.abc import Iterable, Sequence
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlmodel import paginate
from pydantic import BaseModel
from sqlalchemy import ColumnExpressionArgument, UnaryExpression, exc, delete
from sqlmodel import SQLModel, func, select, col
from sqlmodel.ext.asyncio.session import AsyncSession


class OrderEnum(str, Enum):
    ascendent = "ascendent"
    descendent = "descendent"


ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
SchemaType = TypeVar("SchemaType", bound=BaseModel)
T = TypeVar("T", bound=SQLModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType], db: AsyncSession | None = None):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLModel model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model
        self.db = db

    def get_db(self, db: AsyncSession | None) -> AsyncSession:
        db = self.db or db
        assert db is not None, "Database not set"
        return db

    async def get_or_create(
        self,
        condition: ColumnExpressionArgument,
        obj_in: CreateSchemaType | ModelType,
        db: AsyncSession | None = None,
    ) -> ModelType:
        session = self.get_db(db)
        response = await session.exec(
            select(self.model).order_by(col(self.model.id).desc()).where(condition).limit(1)
        )
        obj = response.unique().one_or_none()
        if obj is None:
            obj = self.model.model_validate(obj_in)
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
        return obj

    async def get(
        self, condition: ColumnExpressionArgument, db: AsyncSession | None = None
    ) -> ModelType | None:
        session = self.get_db(db)
        query = select(self.model).where(condition)
        response = await session.exec(query)
        return response.unique().one_or_none()

    async def get_last(
        self, condition: ColumnExpressionArgument, count: int = 1, db: AsyncSession | None = None
    ) -> Sequence[ModelType]:
        session = self.get_db(db)
        query = select(self.model).order_by(col(self.model.updated_at).desc()).where(condition).limit(count)  #  type: ignore
        response = await session.exec(query)
        return response.unique().all()

    async def get_by_ids(
        self,
        *,
        list_ids: list[int | UUID | str],
        db: AsyncSession | None = None,
    ) -> Sequence[ModelType] | None:
        session = self.get_db(db)
        response = await session.exec(select(self.model).where(col(self.model.id).in_(list_ids)))  # type: ignore
        return response.all()

    async def get_count(self, db: AsyncSession | None = None) -> int:
        session = self.get_db(db)
        response = await session.exec(select(func.count()).select_from(select(self.model).subquery()))
        return response.one_or_none() or 0

    async def get_count_by(self, condition: ColumnExpressionArgument, db: AsyncSession | None = None) -> int:
        session = self.get_db(db)
        response = await session.exec(
            select(func.count()).select_from(select(self.model).where(condition).subquery())
        )
        return response.one_or_none() or 0

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        condition: ColumnExpressionArgument | None = None,
        db: AsyncSession | None = None,
    ) -> Sequence[ModelType]:
        session = self.get_db(db)
        _select = select(self.model)
        if condition is not None:
            _select = _select.where(condition)
        _select = _select.limit(limit).offset(skip).order_by(self.model.id)  # type: ignore
        response = await session.exec(_select)
        return response.unique().all()

    async def get_multi_paginated(
        self,
        *,
        params: Params | None = Params(),
        condition: ColumnExpressionArgument | None = None,
        db: AsyncSession | None = None,
    ) -> Page[ModelType]:
        session = self.get_db(db)
        _select = select(self.model)
        if condition is not None:
            _select = _select.where(condition)

        output = await paginate(session=session, query=_select, params=params)
        return output

    async def get_multi_paginated_ordered(
        self,
        params: Params | None = Params(),
        order_by: Iterable[UnaryExpression] | None = None,
        condition: ColumnExpressionArgument | None = None,
        db: AsyncSession | None = None,
    ) -> Page[ModelType]:
        session = self.get_db(db)
        _select = select(self.model)
        if condition is not None:
            _select = _select.where(condition)
        if order_by is not None:
            _select = _select.order_by(*order_by)
        res = await paginate(session=session, query=_select, params=params)
        return res

    async def get_multi_ordered(
        self,
        skip: int = 0,
        limit: int = 100,
        condition: ColumnExpressionArgument | None = None,
        order_by: Iterable[ColumnExpressionArgument] | None = None,
        db: AsyncSession | None = None,
    ) -> Sequence[ModelType]:
        session = self.get_db(db)
        _select = select(self.model)
        if condition is not None:
            _select = _select.where(condition)
        _select = _select.offset(skip).limit(limit)
        if order_by is not None:
            _select = _select.order_by(*order_by)
        response = await session.exec(_select)
        return response.unique().all()

    async def create(
        self,
        obj_in: CreateSchemaType | ModelType,
        db: AsyncSession | None = None,
    ) -> ModelType:
        session = self.get_db(db)
        db_obj = self.model.model_validate(obj_in)

        try:
            session.add(db_obj)
            await session.commit()
            await session.refresh(db_obj)
        except exc.IntegrityError as e:
            await session.rollback()
            raise HTTPException(status_code=409, detail=f"Resource already exists: {str(e)}") from e
        return db_obj


    async def bulk_create(
        self,
        objs_in: list[CreateSchemaType] | list[ModelType],
        db: AsyncSession | None = None,
    ):
        session = self.get_db(db)

        try:
            for obj_in in objs_in:
                db_obj = self.model.model_validate(obj_in)
                session.add(db_obj)
            await session.commit()
        except exc.IntegrityError as e:
            await session.rollback()
            raise HTTPException(status_code=409, detail="One of the resources already exists") from e

    async def update(
        self,
        obj_current: ModelType,
        obj_new: UpdateSchemaType | dict[str, Any] | ModelType,
        db: AsyncSession | None = None,
    ) -> ModelType:
        session = self.get_db(db)

        if isinstance(obj_new, dict):
            update_data = obj_new
        else:
            # This tells Pydantic to not include the values that were not sent
            update_data = obj_new.model_dump(exclude_unset=True)
        for field in update_data:
            setattr(obj_current, field, update_data[field])

        session.add(obj_current)
        await session.commit()
        await session.refresh(obj_current)
        return obj_current

    async def remove(self, condition: ColumnExpressionArgument, db: AsyncSession | None = None) -> ModelType:
        session = self.get_db(db)
        response = await session.exec(select(self.model).where(condition))
        obj = response.unique().one()
        await session.delete(obj)
        await session.commit()
        return obj

    async def remove_all(self, condition: ColumnExpressionArgument, db: AsyncSession | None = None):
        session = self.get_db(db)
        await session.exec(delete(self.model).where(condition))
        await session.commit()
