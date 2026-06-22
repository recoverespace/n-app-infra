from __future__ import annotations

import json
from typing import Any

STRESS_SCORES: dict[str, float] = {
    "very-low": 2,
    "low": 4,
    "mild": 5,
    "medium": 5,
    "moderate": 6,
    "high": 7,
    "very-high": 9,
}

MOOD_FACT_KINDS = ("day-mood-checkin", "emotion-checkin")

MOOD_SCORES: dict[str, float] = {"yes": 8, "no": 3}

EMOTION_SCORES: dict[str, float] = {
    "happy": 9,
    "calm": 8,
    "grateful": 8,
    "hopeful": 8,
    "energetic": 8,
    "okay": 5,
    "confused": 5,
    "apathetic": 4,
    "mood-swings": 4,
    "anxious": 3,
    "sad": 3,
    "depressed": 2,
    "irritated": 3,
    "feeling-guilty": 3,
}

SLEEP_SCORES: dict[str, float] = {"yes": 7, "no": 4}

ENERGY_YES_NO: dict[str, float] = {"yes": 7, "no": 3}

MENTAL_REST_SCORES: dict[str, float] = {
    "relaxed-meditated": 8,
    "walked-moved": 7,
    "no-break": 3,
}

SOCIAL_CONNECTION_SCORE = 6.0

THEMES: list[tuple[str, int]] = [
    ("Academic pressure", 31),
    ("Anxiety", 24),
    ("Loneliness", 19),
    ("Sleep problems", 14),
    ("Homesickness", 12),
    ("Relationships", 11),
    ("Finances", 9),
    ("Burnout", 8),
]

TRACKER_KINDS: list[tuple[str, str, str]] = [
    ("day-mood-checkin", "Mood", "#1D9E75"),
    ("sleep-checkin", "Sleep", "#C79A3B"),
    ("water-checkin", "Water", "#5DCAA5"),
    ("energy-checkin", "Energy", "#E0902F"),
    ("food-logging", "Food", "#D85A30"),
    ("alcohol-checkin", "Alcohol", "#B07A8C"),
]

DIMENSION_CONFIG: list[tuple[str, str, str, str | tuple[str, ...]]] = [
    ("Mood", "day-mood-checkin", "#1D9E75", MOOD_FACT_KINDS),
    ("Stress", "stress-checkin", "#D85A30", "stress-checkin"),
    ("Energy", "energy-checkin", "#E0902F", "energy-checkin"),
    ("Sleep", "sleep-checkin", "#C79A3B", "sleep-checkin"),
    ("Connection", "social-connection-checkin", "#534AB7", "social-connection-checkin"),
    ("Focus", "mental-rest-checkin", "#1D9E75", "mental-rest-checkin"),
]

WELLBEING_KINDS = {
    "day-mood-checkin": "mood",
    "emotion-checkin": "mood",
    "stress-checkin": "stress",
    "sleep-checkin": "sleep",
}

LOW_MOOD_THRESHOLD = 4
HIGH_STRESS_THRESHOLD = 7


def parse_fact_data(value: str | dict) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def first_option(data: dict[str, Any]) -> str | None:
    options = data.get("options") or []
    if not options:
        return None
    first = options[0]
    if isinstance(first, list):
        return str(first[0]) if first else None
    return str(first) if first is not None else None


def score_userfact(kind: str, value: str | dict) -> float | None:
    data = parse_fact_data(value)
    option = first_option(data)
    if option is None and kind != "social-connection-checkin":
        return None

    if kind == "stress-checkin":
        return STRESS_SCORES.get(option or "", None)
    if kind == "day-mood-checkin":
        return MOOD_SCORES.get(option or "", None)
    if kind == "emotion-checkin":
        return EMOTION_SCORES.get(option or "", None)
    if kind == "sleep-checkin":
        extra = data.get("extraInfo")
        if extra:
            try:
                extra_info = json.loads(extra) if isinstance(extra, str) else extra
                if isinstance(extra_info, dict):
                    bed = extra_info.get("startTime")
                    wake = extra_info.get("endTime")
                    if bed and wake:
                        from datetime import datetime

                        start = datetime.fromisoformat(str(bed).replace("Z", "+00:00"))
                        end = datetime.fromisoformat(str(wake).replace("Z", "+00:00"))
                        hours = (end - start).total_seconds() / 3600
                        if hours < 0:
                            hours += 24
                        return max(1.0, min(10.0, hours / 0.9))
            except (ValueError, TypeError, json.JSONDecodeError):
                pass
        return SLEEP_SCORES.get(option or "", None)
    if kind == "energy-checkin":
        if option and "/" in option:
            try:
                return float(option.split("/")[0])
            except ValueError:
                pass
        if option:
            try:
                return float(option)
            except ValueError:
                return ENERGY_YES_NO.get(option)
        return None
    if kind == "mental-rest-checkin":
        return MENTAL_REST_SCORES.get(option or "", None)
    if kind == "social-connection-checkin":
        return SOCIAL_CONNECTION_SCORE
    return None
