from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import mean

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from admin.dashboard.mapping import (
    DIMENSION_CONFIG,
    HIGH_STRESS_THRESHOLD,
    LOW_MOOD_THRESHOLD,
    MOOD_FACT_KINDS,
    THEMES,
    TRACKER_KINDS,
    WELLBEING_KINDS,
    score_userfact,
)
from admin.dashboard.schemas import (
    AiMetrics,
    CommunityPoint,
    DashboardStats,
    DimensionItem,
    PeriodInfo,
    SummaryMetrics,
    TenantInfo,
    ThemeItem,
    TrackerUsage,
    WellbeingTrendPoint,
)
from data.domain.chat_messages.models import ChatMessage
from data.domain.chats.models import Chat
from data.domain.community.models import Comment, Post, Reaction
from data.domain.facts.models import UserFact
from data.domain.tenants.models import Tenant
from data.domain.users.models import User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_period() -> tuple[datetime, datetime, str]:
    to_dt = _utc_now()
    from_dt = to_dt - timedelta(days=30)
    return from_dt, to_dt, "Last 30 days"


def parse_period(
    from_str: str | None, to_str: str | None, label: str | None = None
) -> tuple[datetime, datetime, str]:
    if from_str and to_str:
        from_dt = datetime.fromisoformat(from_str).replace(tzinfo=timezone.utc)
        to_dt = datetime.fromisoformat(to_str).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        period_label = label or f"{from_dt.date().isoformat()} – {to_dt.date().isoformat()}"
        return from_dt, to_dt, period_label
    return default_period()


def bucket_unit(from_dt: datetime, to_dt: datetime) -> str:
    days = max(1, (to_dt.date() - from_dt.date()).days + 1)
    if days <= 14:
        return "day"
    if days <= 84:
        return "week"
    return "month"


def bucket_key(dt: datetime, unit: str) -> date:
    d = dt.date() if isinstance(dt, datetime) else dt
    if unit == "day":
        return d
    if unit == "week":
        return d - timedelta(days=d.weekday())
    return d.replace(day=1)


def iter_bucket_keys(from_dt: datetime, to_dt: datetime, unit: str) -> list[date]:
    from_d = from_dt.date()
    to_d = to_dt.date()
    keys: list[date] = []
    if unit == "day":
        d = from_d
        while d <= to_d:
            keys.append(d)
            d += timedelta(days=1)
    elif unit == "week":
        d = from_d - timedelta(days=from_d.weekday())
        while d <= to_d:
            keys.append(d)
            d += timedelta(days=7)
    else:
        d = from_d.replace(day=1)
        while d <= to_d:
            keys.append(d)
            if d.month == 12:
                d = date(d.year + 1, 1, 1)
            else:
                d = date(d.year, d.month + 1, 1)
    return keys


def bucket_label_for_key(key: date, unit: str, from_dt: datetime, to_dt: datetime) -> str:
    span_years = from_dt.year != to_dt.year
    if unit == "day":
        return key.strftime("%d %b")
    if unit == "week":
        end = key + timedelta(days=6)
        if key.month == end.month:
            return f"{key.day}–{end.day} {key.strftime('%b')}"
        return f"{key.day} {key.strftime('%b')}–{end.day} {end.strftime('%b')}"
    fmt = "%b '%y" if span_years else "%b"
    return key.strftime(fmt)


def pct(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return round(numerator / denominator * 100)


async def get_tenant(db: AsyncSession, tenant_id: int) -> Tenant | None:
    result = await db.exec(select(Tenant).where(Tenant.id == tenant_id))
    return result.first()


async def get_tenant_user_ids(db: AsyncSession, tenant_id: int) -> list[int]:
    result = await db.exec(
        select(User.id).where(User.tenant_id == tenant_id, User.is_deleted == False)  # noqa: E712
    )
    return list(result.all())


async def get_active_user_ids(
    db: AsyncSession,
    tenant_id: int,
    user_ids: list[int],
    from_dt: datetime,
    to_dt: datetime,
) -> set[int]:
    if not user_ids:
        return set()

    active: set[int] = set()

    fact_rows = await db.exec(
        select(UserFact.user_id)
        .join(User, User.id == UserFact.user_id)
        .where(
            User.tenant_id == tenant_id,
            UserFact.created_at >= from_dt,
            UserFact.created_at <= to_dt,
        )
        .distinct()
    )
    active.update(fact_rows.all())

    for model, user_col in (
        (Post, Post.user_id),
        (Comment, Comment.user_id),
        (Reaction, Reaction.user_id),
    ):
        rows = await db.exec(
            select(user_col)
            .where(
                model.tenant_id == tenant_id,
                model.created_at >= from_dt,
                model.created_at <= to_dt,
            )
            .distinct()
        )
        active.update(rows.all())

    chat_rows = await db.exec(
        select(Chat.user_id)
        .join(ChatMessage, ChatMessage.chat_id == Chat.id)
        .join(User, User.id == Chat.user_id)
        .where(
            User.tenant_id == tenant_id,
            ChatMessage.created_at >= from_dt,
            ChatMessage.created_at <= to_dt,
        )
        .distinct()
    )
    active.update(chat_rows.all())

    return active


async def get_p2p_user_ids(
    db: AsyncSession, tenant_id: int, from_dt: datetime, to_dt: datetime
) -> set[int]:
    p2p: set[int] = set()
    for model, user_col in (
        (Post, Post.user_id),
        (Comment, Comment.user_id),
        (Reaction, Reaction.user_id),
    ):
        rows = await db.exec(
            select(user_col)
            .where(
                model.tenant_id == tenant_id,
                model.created_at >= from_dt,
                model.created_at <= to_dt,
            )
            .distinct()
        )
        p2p.update(rows.all())
    return p2p


async def get_support_zone_user_ids(
    db: AsyncSession,
    tenant_id: int,
    active_user_ids: set[int],
    from_dt: datetime,
    to_dt: datetime,
) -> set[int]:
    if not active_user_ids:
        return set()

    rows = await db.exec(
        select(UserFact)
        .join(User, User.id == UserFact.user_id)
        .where(
            User.tenant_id == tenant_id,
            UserFact.kind.in_([*MOOD_FACT_KINDS, "stress-checkin"]),
            UserFact.created_at >= from_dt,
            UserFact.created_at <= to_dt,
            UserFact.user_id.in_(active_user_ids),
        )
    )
    facts = list(rows.all())

    mood_by_user: dict[int, list[float]] = defaultdict(list)
    stress_by_user: dict[int, list[float]] = defaultdict(list)
    for fact in facts:
        score = score_userfact(fact.kind, fact.value)
        if score is None:
            continue
        if fact.kind in MOOD_FACT_KINDS:
            mood_by_user[fact.user_id].append(score)
        else:
            stress_by_user[fact.user_id].append(score)

    support: set[int] = set()
    for user_id in active_user_ids:
        moods = mood_by_user.get(user_id, [])
        stresses = stress_by_user.get(user_id, [])
        if not moods or not stresses:
            continue
        if min(moods) <= LOW_MOOD_THRESHOLD and max(stresses) >= HIGH_STRESS_THRESHOLD:
            support.add(user_id)
    return support


def build_wellbeing_trend(
    facts: list[UserFact], from_dt: datetime, to_dt: datetime, unit: str
) -> list[WellbeingTrendPoint]:
    buckets: dict[date, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for fact in facts:
        if fact.kind not in WELLBEING_KINDS:
            continue
        score = score_userfact(fact.kind, fact.value)
        if score is None:
            continue
        key = bucket_key(fact.created_at, unit)
        buckets[key][WELLBEING_KINDS[fact.kind]].append(score)

    points: list[WellbeingTrendPoint] = []
    for key in iter_bucket_keys(from_dt, to_dt, unit):
        data = buckets.get(key, {})
        points.append(
            WellbeingTrendPoint(
                label=bucket_label_for_key(key, unit, from_dt, to_dt),
                mood=round(mean(data["mood"]), 1) if data.get("mood") else None,
                stress=round(mean(data["stress"]), 1) if data.get("stress") else None,
                sleep=round(mean(data["sleep"]), 1) if data.get("sleep") else None,
            )
        )
    return points


async def build_community_trend(
    db: AsyncSession, tenant_id: int, from_dt: datetime, to_dt: datetime, unit: str
) -> list[CommunityPoint]:
    buckets: dict[date, dict[str, int]] = defaultdict(lambda: {"posts": 0, "comments": 0, "reactions": 0})

    for model, field in ((Post, "posts"), (Comment, "comments"), (Reaction, "reactions")):
        rows = await db.exec(
            select(model).where(
                model.tenant_id == tenant_id,
                model.created_at >= from_dt,
                model.created_at <= to_dt,
            )
        )
        for row in rows.all():
            key = bucket_key(row.created_at, unit)
            buckets[key][field] += 1

    return [
        CommunityPoint(
            label=bucket_label_for_key(key, unit, from_dt, to_dt),
            posts=buckets.get(key, {}).get("posts", 0),
            comments=buckets.get(key, {}).get("comments", 0),
            reactions=buckets.get(key, {}).get("reactions", 0),
        )
        for key in iter_bucket_keys(from_dt, to_dt, unit)
    ]


def build_trackers(
    facts: list[UserFact], active_count: int, active_user_ids: set[int]
) -> list[TrackerUsage]:
    if active_count <= 0:
        return []

    users_by_kind: dict[str, set[int]] = defaultdict(set)
    for fact in facts:
        if fact.user_id not in active_user_ids:
            continue
        users_by_kind[fact.kind].add(fact.user_id)

    trackers: list[TrackerUsage] = []
    for kind, name, color in TRACKER_KINDS:
        count = len(users_by_kind.get(kind, set()))
        trackers.append(TrackerUsage(name=name, pct=pct(count, active_count), color=color))
    trackers.sort(key=lambda t: t.pct, reverse=True)
    return trackers


async def build_ai_metrics(
    db: AsyncSession,
    tenant_id: int,
    from_dt: datetime,
    to_dt: datetime,
    unit: str,
    active_count: int,
) -> AiMetrics:
    rows = await db.exec(
        select(ChatMessage.created_at, Chat.user_id)
        .join(Chat, Chat.id == ChatMessage.chat_id)
        .join(User, User.id == Chat.user_id)
        .where(
            User.tenant_id == tenant_id,
            ChatMessage.role == "assistant",
            ChatMessage.created_at >= from_dt,
            ChatMessage.created_at <= to_dt,
        )
    )
    row_list = list(rows.all())
    users_with_ai: set[int] = set()
    buckets: dict[date, int] = defaultdict(int)
    for created_at, chat_user_id in row_list:
        if chat_user_id:
            users_with_ai.add(chat_user_id)
        buckets[bucket_key(created_at, unit)] += 1

    trend = [
        {
            "label": bucket_label_for_key(key, unit, from_dt, to_dt),
            "count": buckets.get(key, 0),
        }
        for key in iter_bucket_keys(from_dt, to_dt, unit)
    ]

    return AiMetrics(
        total_reflections=len(row_list),
        engagement_pct=pct(len(users_with_ai), active_count),
        trend=trend,
    )


def latest_per_user_per_day(facts: list[UserFact]) -> list[UserFact]:
    latest: dict[tuple[int, str, date], UserFact] = {}
    for fact in facts:
        day = fact.created_at.date()
        key = (fact.user_id, fact.kind, day)
        if key not in latest or fact.created_at > latest[key].created_at:
            latest[key] = fact
    return list(latest.values())


def build_dimensions(facts: list[UserFact]) -> list[DimensionItem]:
    deduped = latest_per_user_per_day(facts)
    scores_by_kind: dict[str, list[float]] = defaultdict(list)
    for fact in deduped:
        score = score_userfact(fact.kind, fact.value)
        if score is not None:
            scores_by_kind[fact.kind].append(score)

    dimensions: list[DimensionItem] = []
    for name, kind, color, fact_kinds in DIMENSION_CONFIG:
        kinds = fact_kinds if isinstance(fact_kinds, tuple) else (kind,)
        values: list[float] = []
        for k in kinds:
            values.extend(scores_by_kind.get(k, []))
        value = round(mean(values), 1) if values else None
        dimensions.append(DimensionItem(name=name, value=value, color=color))
    return dimensions


async def get_dashboard_stats(
    db: AsyncSession,
    tenant_id: int,
    from_str: str | None = None,
    to_str: str | None = None,
    period_label: str | None = None,
) -> DashboardStats:
    tenant = await get_tenant(db, tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant {tenant_id} not found")

    from_dt, to_dt, label = parse_period(from_str, to_str, period_label)
    unit = bucket_unit(from_dt, to_dt)

    user_ids = await get_tenant_user_ids(db, tenant_id)
    total_registered = len(user_ids)
    active_user_ids = await get_active_user_ids(db, tenant_id, user_ids, from_dt, to_dt)
    active_count = len(active_user_ids)

    p2p_user_ids = await get_p2p_user_ids(db, tenant_id, from_dt, to_dt)
    p2p_active = p2p_user_ids & active_user_ids

    support_users = await get_support_zone_user_ids(db, tenant_id, active_user_ids, from_dt, to_dt)

    wellbeing_kinds = list(WELLBEING_KINDS.keys())
    dimension_kinds = [kind for _, kind, _, _ in DIMENSION_CONFIG]
    tracker_kinds = [k for k, _, _ in TRACKER_KINDS]
    all_kinds = list(set(wellbeing_kinds + dimension_kinds + tracker_kinds))

    if user_ids:
        fact_result = await db.exec(
            select(UserFact).where(
                UserFact.user_id.in_(user_ids),
                UserFact.kind.in_(all_kinds),
                UserFact.created_at >= from_dt,
                UserFact.created_at <= to_dt,
            )
        )
        facts = list(fact_result.all())
    else:
        facts = []

    wellbeing_facts = [f for f in facts if f.kind in WELLBEING_KINDS]

    return DashboardStats(
        tenant=TenantInfo(id=tenant.id, title=tenant.title),
        period=PeriodInfo(from_date=from_dt.date(), to_date=to_dt.date(), label=label),
        summary=SummaryMetrics(
            total_registered=total_registered,
            active_users=active_count,
            active_pct=pct(active_count, total_registered),
            p2p_engagement_pct=pct(len(p2p_active), active_count),
            support_zone_pct=pct(len(support_users), active_count),
        ),
        wellbeing_trend=build_wellbeing_trend(wellbeing_facts, from_dt, to_dt, unit),
        community=await build_community_trend(db, tenant_id, from_dt, to_dt, unit),
        trackers=build_trackers(facts, active_count, active_user_ids),
        ai=await build_ai_metrics(db, tenant_id, from_dt, to_dt, unit, active_count),
        themes=[ThemeItem(name=name, pct=pct_val) for name, pct_val in THEMES],
        dimensions=build_dimensions(facts),
    )
