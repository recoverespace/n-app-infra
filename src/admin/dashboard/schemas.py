from datetime import date, datetime

from pydantic import BaseModel


class TenantInfo(BaseModel):
    id: int
    title: str


class PeriodInfo(BaseModel):
    from_date: date
    to_date: date
    label: str


class SummaryMetrics(BaseModel):
    total_registered: int
    active_users: int
    active_pct: int
    p2p_engagement_pct: int
    support_zone_pct: int


class WellbeingTrendPoint(BaseModel):
    label: str
    mood: float | None = None
    stress: float | None = None
    sleep: float | None = None


class CommunityPoint(BaseModel):
    label: str
    posts: int
    comments: int
    reactions: int


class TrackerUsage(BaseModel):
    name: str
    pct: int
    color: str


class AiMetrics(BaseModel):
    total_reflections: int
    engagement_pct: int
    trend: list[dict[str, int | str]]


class ThemeItem(BaseModel):
    name: str
    pct: int


class DimensionItem(BaseModel):
    name: str
    value: float | None
    color: str


class DashboardStats(BaseModel):
    tenant: TenantInfo
    period: PeriodInfo
    summary: SummaryMetrics
    wellbeing_trend: list[WellbeingTrendPoint]
    community: list[CommunityPoint]
    trackers: list[TrackerUsage]
    ai: AiMetrics
    themes: list[ThemeItem]
    dimensions: list[DimensionItem]

    def model_dump_json_compatible(self) -> dict:
        data = self.model_dump()
        data["period"] = {
            "from": self.period.from_date.isoformat(),
            "to": self.period.to_date.isoformat(),
            "label": self.period.label,
        }
        return data
