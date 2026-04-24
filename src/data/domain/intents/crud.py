from collections.abc import Sequence
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession

from data.lib.crud import CRUDBase
from data.domain.intents.schemas import TemplateOverrideCreate, TemplateOverrideUpdate
from data.domain.intents.models import TemplateOverride


class CRUDTemplateOverride(CRUDBase[TemplateOverride, TemplateOverrideCreate, TemplateOverrideUpdate]):
    async def get_for_user(
        self,
        user_id: int | UUID | str,
        db: AsyncSession | None = None,
    ) -> Sequence[TemplateOverride]:
        return []


crud_template_override = CRUDTemplateOverride(TemplateOverride)
