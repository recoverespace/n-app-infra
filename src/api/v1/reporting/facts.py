from fastapi import APIRouter, Depends
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from api.lib.deps import DBDep
from data.domain.facts.models import UserFact
from data.domain.facts.schemas import UserFactRead

from .schemas import FactFilter, PaginatedResponse

router = APIRouter()


async def build_fact_query(filters: FactFilter, base_query):
    if filters.user_id:
        base_query = base_query.where(UserFact.user_id == filters.user_id)
    if filters.kind:
        base_query = base_query.where(UserFact.kind == filters.kind)
    if filters.label:
        base_query = base_query.where(UserFact.label == filters.label)

    # Date range filter
    if filters.start_date:
        base_query = base_query.where(UserFact.created_at >= filters.start_date)
    if filters.end_date:
        base_query = base_query.where(UserFact.created_at <= filters.end_date)

    # Sorting
    if filters.sort_by:
        sort_column = getattr(UserFact, filters.sort_by, None)
        if sort_column:
            if filters.sort_order == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column)
    else:
        base_query = base_query.order_by(UserFact.created_at.desc())

    return base_query


@router.get("/facts/", summary="List all facts (searchable)")
async def list_facts(filters: FactFilter = Depends(), db: AsyncSession = DBDep) -> PaginatedResponse:
    base_query = select(UserFact)
    query = await build_fact_query(filters, base_query)

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    query = query.offset(offset).limit(filters.size)

    facts = (await db.exec(query)).unique()

    return PaginatedResponse(
        items=[UserFactRead.model_validate(fact).model_dump() for fact in facts],
        page=filters.page,
        size=filters.size,
    )
