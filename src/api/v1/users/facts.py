from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException, Query, status
from fastapi_pagination import Page, Params
from sqlmodel import and_, col

from api.lib.deps import DBDep, UserIDDep
from data.domain.facts.crud import user_fact_crud
from data.domain.facts.models import UserFact
from data.domain.facts.schemas import UserFactCreate, UserFactRead, UserFactUpdate

router = APIRouter(prefix="/me/facts")


@router.get("/")
async def get_user_facts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    kind: str = Query(""),
    size_by_kind: int | None = Query(
        None, ge=1, le=100, description="Number of items to return per kind"
    ),
    get_all: bool = Query(False, description="Get all facts within date range"),
    user_id=UserIDDep,
    db=DBDep,
) -> Page[UserFactRead]:
    condition = and_(
        col(UserFact.user_id) == user_id,
    )
    if start_date is not None:
        condition = and_(condition, col(UserFact.created_at) >= start_date)
    if end_date is not None:
        condition = and_(condition, col(UserFact.created_at) < end_date)
    if kind != "":
        condition = and_(condition, col(UserFact.kind) == kind)

    if get_all:
        facts = await user_fact_crud.get_all(condition=condition, db=db)
        return Page(
            items=[UserFactRead.from_orm(f) for f in facts],
            total=len(facts),
            page=1,
            size=max(1, len(facts)),
            pages=1,
        )

    if size_by_kind is not None:
        facts = await user_fact_crud.get_facts_by_kind(
            condition=condition,
            size_by_kind=size_by_kind,
            db=db,
        )
        return Page(
            items=[UserFactRead.from_orm(f) for f in facts],
            total=len(facts),
            page=1,
            size=max(1, len(facts)),
            pages=1,
        )

    return await user_fact_crud.get_multi_paginated_ordered(
        params=Params(page=page, size=size),
        condition=condition,
        order_by=(col(UserFact.created_at).desc(),),
        db=db,
    )  # type: ignore


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user_fact(
    data: UserFactCreate | list[UserFactCreate], user_id=UserIDDep, db=DBDep
):
    if not isinstance(data, list):
        data = [data]
    for d in data:
        d.user_id = user_id
        d.created_at = datetime.now(UTC) if not d.created_at else d.created_at
        d.updated_at = datetime.now(UTC) if not d.updated_at else d.updated_at
    await user_fact_crud.bulk_create(data, db=db)


@router.patch("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_user_fact(
    fact_id: int,
    data: UserFactUpdate,
    user_id=UserIDDep,
    db=DBDep,
):
    fact = await user_fact_crud.get(col(UserFact.id) == fact_id, db)
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found"
        )
    await user_fact_crud.update(
        fact,
        data,
        db=db,
    )


@router.delete("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_fact(
    fact_id: int,
    user_id=UserIDDep,
    db=DBDep,
):
    await user_fact_crud.remove(
        and_(
            UserFact.id == fact_id,
            UserFact.user_id == user_id,
        ),
        db=db,
    )
