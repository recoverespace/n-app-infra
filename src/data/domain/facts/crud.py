from collections.abc import Sequence
from datetime import date, datetime, timedelta
from uuid import UUID
from data.domain.facts.schemas import UserFactCreate, UserFactUpdate
from data.domain.facts.models import UserFact
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, col
from sqlalchemy.orm import aliased

from data.lib.crud import CRUDBase


class CRUDUserFact(CRUDBase[UserFact, UserFactCreate, UserFactUpdate]):
    async def get_last_fact(self, user_id: int | UUID | str, kind: str, db: AsyncSession | None = None) -> UserFact | None:
        session = self.get_db(db)
        query = (
            select(UserFact).where(UserFact.user_id == user_id, UserFact.kind == kind).order_by(col(UserFact.created_at).desc()).limit(1)
        )
        response = await session.exec(query)
        return response.one_or_none()

    async def get_all_last_facts(
        self,
        user_id: int | UUID | str,
        limit: int,
        max_days: int = 14,
        db: AsyncSession | None = None,
    ) -> Sequence[UserFact]:
        offset = datetime.now() - timedelta(days=max_days)
        session = self.get_db(db)
        query = (
            select(UserFact)
            .where(
                col(UserFact.user_id) == user_id,
                col(UserFact.created_at) >= offset,
            )
            .order_by(col(UserFact.created_at).desc())
            .limit(limit)
        )
        response = await session.exec(query)
        return response.all()

    async def get_last_facts(
        self,
        user_id: int | UUID | str,
        kind: str,
        limit: int,
        day_offset: int,
        db: AsyncSession | None = None,
    ) -> Sequence[UserFact]:
        offset = datetime.now() - timedelta(days=day_offset)
        session = self.get_db(db)
        query = (
            select(UserFact)
            .where(
                col(UserFact.user_id) == user_id,
                col(UserFact.kind) == kind,
                col(UserFact.created_at) <= offset,
            )
            .order_by(col(UserFact.created_at).desc())
            .limit(limit)
        )
        response = await session.exec(query)
        return response.all()

    async def get_summary(
        self,
        user_id: int | UUID | str,
        start_date: date,
        kind: list[str],
        days: int = 7,
        db: AsyncSession | None = None,
    ) -> Sequence[UserFact]:
        session = self.get_db(db)
        end_date = start_date - timedelta(days=days)
        query = (
            select(UserFact)
            .where(
                col(UserFact.user_id) == user_id,
                col(UserFact.kind).in_(kind),
                col(UserFact.created_at) >= end_date,
                col(UserFact.created_at) < start_date,
            )
            .order_by(col(UserFact.kind), col(UserFact.created_at).desc())
        )
        response = await session.exec(query)
        return response.all()

    async def get_summary_count(
        self,
        user_id: int | UUID | str,
        start_date: date,
        kinds: list[str],
        days: int = 7,
        db: AsyncSession | None = None,
    ) -> dict[str, int]:
        session = self.get_db(db)
        end_date = start_date - timedelta(days=days)
        query = (
            select(UserFact.kind, func.count())
            .where(
                col(UserFact.user_id) == user_id,
                col(UserFact.kind).in_(kinds),
                col(UserFact.created_at) >= end_date,
                col(UserFact.created_at) < start_date,
            )
            .group_by(UserFact.kind)
        )
        response = await session.exec(query)
        result = {}
        for kind, count in response:
            result[kind] = count
        return result

    async def get_all(
        self,
        condition,
        db: AsyncSession | None = None,
    ) -> Sequence[UserFact]:
        session = self.get_db(db)
        result = await session.exec(select(UserFact).where(condition))
        return result.all()

    async def get_facts_by_kind(
        self,
        condition,
        size_by_kind: int,
        db: AsyncSession | None = None,
    ) -> Sequence[UserFact]:
        session = self.get_db(db)

        subquery = (
            select(
                UserFact,
                func.row_number().over(partition_by=UserFact.kind, order_by=UserFact.created_at.desc()).label("rn"),
            )
            .where(condition)
            .subquery()
        )

        aliased_fact = aliased(UserFact, subquery)
        query = select(aliased_fact).where(subquery.c.rn <= size_by_kind)

        result = await session.exec(query)
        return result.all()


user_fact_crud = CRUDUserFact(UserFact)
