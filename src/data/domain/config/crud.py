from datetime import date
from typing import Any

from sqlmodel import and_, select, col
from data.domain.config.schemas import ConfigCreate, ConfigUpdate
from data.domain.config.models import Config

from sqlmodel.ext.asyncio.session import AsyncSession
from data.lib.crud import CRUDBase
from common.otel import get_logger

logger = get_logger(__name__)


class CRUDDevice(CRUDBase[Config, ConfigCreate, ConfigUpdate]):
    async def get_for_segments(
        self, segments: list[str], for_date: date | None = None, db: AsyncSession|None=None
    ) -> dict[str, Any]:
        session = self.get_db(db)
        for_date = for_date or date.today()
        query = (
            select(Config)
            .where(
                and_(
                    col(Config.segment).in_(segments),
                    col(Config.start_date) <= for_date,
                    col(Config.end_date) >= for_date,
                    col(Config.enabled) is True,
                )
            )
            .order_by(col(Config.priority).desc())
        )
        response = await session.exec(query)
        configs = list(response.unique().all())
        if not configs:
            logger.warning(f"No config found for segments {segments} and date {for_date}")
            return {}
        config = configs[0].overrides.get_config({})
        for c in configs[1:]:
            config = c.overrides.get_config(config)
        return config


config_crud = CRUDDevice(Config)
