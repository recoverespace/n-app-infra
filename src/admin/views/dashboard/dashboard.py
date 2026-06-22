import json

from sqladmin import BaseView, expose
from sqlmodel import select
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from admin.dashboard.service import get_dashboard_stats
from data.domain.tenants.models import Tenant
from data.lib.db import SessionLocal


def _as_tenant(row: object) -> Tenant | None:
    if isinstance(row, Tenant):
        return row
    try:
        first = row[0]  # type: ignore[index]
        if isinstance(first, Tenant):
            return first
    except (TypeError, KeyError, IndexError):
        pass
    return None


class DashboardView(BaseView):
    name = "Wellbeing Dashboard"
    category = "User Management"
    icon = "fa-solid fa-chart-line"

    @expose("/dashboard", methods=["GET"])
    async def dashboard_page(self, request: Request):
        tenant_id = request.query_params.get("tenant_id")
        if not tenant_id:
            return RedirectResponse(url="/admin/tenant/list", status_code=302)

        try:
            tid = int(tenant_id)
        except ValueError:
            return RedirectResponse(url="/admin/tenant/list", status_code=302)

        tenant_title = "Tenant"
        tenants: list[dict[str, int | str]] = []
        async with SessionLocal() as db:
            result = await db.exec(select(Tenant).order_by(Tenant.id))
            for row in result.all():
                tenant = _as_tenant(row)
                if tenant is None:
                    continue
                tenants.append({"id": tenant.id, "title": tenant.title})
                if tenant.id == tid:
                    tenant_title = tenant.title

        return await self.templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "tenant_id": tid,
                "tenant_title": tenant_title,
                "tenants_json": json.dumps(tenants),
            },
        )

    @expose("/dashboard/stats", methods=["GET"])
    async def dashboard_stats(self, request: Request):
        tenant_id = request.query_params.get("tenant_id")
        if not tenant_id:
            return JSONResponse({"error": "tenant_id is required"}, status_code=400)

        try:
            tid = int(tenant_id)
        except ValueError:
            return JSONResponse({"error": "invalid tenant_id"}, status_code=400)

        from_str = request.query_params.get("from")
        to_str = request.query_params.get("to")
        period_label = request.query_params.get("label")

        try:
            async with SessionLocal() as db:
                stats = await get_dashboard_stats(
                    db, tid, from_str=from_str, to_str=to_str, period_label=period_label
                )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)

        return JSONResponse(stats.model_dump_json_compatible())
