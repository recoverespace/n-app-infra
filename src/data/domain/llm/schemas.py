from __future__ import annotations

import json
from typing import Any
from datetime import date, datetime, time

from pydantic import BaseModel

from common.otel import get_logger
from data.domain.facts.schemas import UserFactBase as UserFact
from data.domain.users.schemas import UserBase

logger = get_logger(__name__)


class StressCheckin(BaseModel):
    type: str = "stress"
    value: str | None = None
    level: int | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False) -> StressCheckin:
        if user_fact.kind != "stress-checkin":
            raise ValueError("UserFact kind must be 'stress-checkin'")

        # Extract level from options
        level = None
        stress_value = None
        if data.get("options") and len(data["options"]) > 0:
            stress_value = data["options"][0]
            stress_map = {"very-low": 1, "low": 2, "medium": 3, "high": 4, "very-high": 5}
            level = stress_map.get(stress_value, None)

        return cls(
            value=stress_value,
            level=level,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class SleepCheckin(BaseModel):
    type: str = "sleep"
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    slept_well: bool | None = None
    bed_time: time | None = None
    wake_time: time | None = None
    sleep_hours: float | None = None
    activity_type: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False) -> SleepCheckin:
        if user_fact.kind != "sleep-checkin":
            raise ValueError("UserFact kind must be 'sleep-checkin'")

        # Parse sleep quality from options
        slept_well = None
        if data.get("options") and len(data["options"]) > 0:
            slept_well = data["options"][0] == "yes"

        # Parse extra info for sleep details
        extra_info = {}
        if data.get("extraInfo"):
            try:
                extra_info = (
                    json.loads(data["extraInfo"]) if isinstance(data["extraInfo"], str) else data["extraInfo"]
                )
            except json.JSONDecodeError:
                pass

        # Parse times from extraInfo
        bed_time = None
        wake_time = None
        if "startTime" in extra_info:
            try:
                start_dt = datetime.fromisoformat(extra_info["startTime"].replace("Z", "+00:00"))
                bed_time = start_dt.time()
            except (ValueError, TypeError):
                pass

        if "endTime" in extra_info:
            try:
                end_dt = datetime.fromisoformat(extra_info["endTime"].replace("Z", "+00:00"))
                wake_time = end_dt.time()
            except (ValueError, TypeError):
                pass

        # Calculate sleep hours if both times available
        sleep_hours = None
        if bed_time and wake_time:
            bed_minutes = bed_time.hour * 60 + bed_time.minute
            wake_minutes = wake_time.hour * 60 + wake_time.minute
            if wake_minutes < bed_minutes:  # Next day
                wake_minutes += 24 * 60
            sleep_hours = (wake_minutes - bed_minutes) / 60

        return cls(
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            slept_well=slept_well,
            bed_time=bed_time,
            wake_time=wake_time,
            sleep_hours=sleep_hours,
            is_new=is_new,
        )


class EmotionCheckin(BaseModel):
    type: str = "emotion"
    value: str | None = None
    valence: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> EmotionCheckin:
        if user_fact.kind != "emotion-checkin":
            raise ValueError("UserFact kind must be 'emotion-checkin'")

        # Get emotion from options
        emotion = None
        if data.get("options") and len(data["options"]) > 0:
            emotion = data["options"][0]

        # Determine valence from emotion
        valence = None
        if emotion:
            positive_emotions = ["happy", "joyful", "excited", "grateful", "content", "peaceful", "relaxed"]
            negative_emotions = [
                "sad",
                "anxious",
                "angry",
                "frustrated",
                "overwhelmed",
                "stressed",
                "tired",
                "worried",
            ]
            emotion_lower = emotion.lower()
            if any(pos in emotion_lower for pos in positive_emotions):
                valence = "positive"
            elif any(neg in emotion_lower for neg in negative_emotions):
                valence = "negative"
            else:
                valence = "neutral"

        return cls(
            value=emotion,
            valence=valence,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class BingeEatingCheckin(BaseModel):
    type: str = "binge_eating"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    intensity: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> BingeEatingCheckin:
        if user_fact.kind != "binge-eating":
            raise ValueError("UserFact kind must be 'binge-eating'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        # Parse intensity from extraInfo
        intensity = None
        if data.get("extraInfo"):
            try:
                extra_info = (
                    json.loads(data["extraInfo"]) if isinstance(data["extraInfo"], str) else data["extraInfo"]
                )
                intensity = extra_info.get("intensity")
            except json.JSONDecodeError:
                pass

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            intensity=intensity,
            is_new=is_new,
        )


class FoodLogCheckin(BaseModel):
    type: str = "food_log"
    value: str | None = None  # Meal type
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    feeling: str | None = None
    description: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> FoodLogCheckin:
        if user_fact.kind != "food-logging":
            raise ValueError("UserFact kind must be 'food-logging'")

        # Get meal type from options
        meal_type = None
        if data.get("options") and len(data["options"]) > 0:
            meal_type = data["options"][0]

        # Parse feeling and description from extraInfo
        feeling = None
        description = None
        if data.get("extraInfo"):
            try:
                extra_info = (
                    json.loads(data["extraInfo"]) if isinstance(data["extraInfo"], str) else data["extraInfo"]
                )
                feeling = extra_info.get("feeling")
                description = extra_info.get("description")
            except json.JSONDecodeError:
                pass

        return cls(
            value=meal_type,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            feeling=feeling,
            description=description,
            is_new=is_new,
        )


class EatingAttitudeTestCheckin(BaseModel):
    type: str = "eating_attitude_test"
    timestamp: datetime | None = None
    created_at: datetime | None = None
    score: int | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> EatingAttitudeTestCheckin:
        if user_fact.kind == "eat-9":
            try:
                data = json.loads(user_fact.value)
                score = None
                if data.get("options") and len(data["options"]) > 0:
                    try:
                        score = int(data["options"][0])
                    except ValueError:
                        pass
                return cls(score=score, is_new=is_new, created_at=user_fact.created_at)
            except json.JSONDecodeError:
                raise ValueError("UserFact value is not valid JSON")
        elif user_fact.kind == "eating_attitude":
            # Simple string value
            try:
                score = int(user_fact.value)
            except ValueError:
                score = None
            return cls(score=score, is_new=is_new, created_at=user_fact.created_at)
        else:
            raise ValueError("UserFact kind must be 'eat-9' or 'eating_attitude'")


class JournalCheckin(BaseModel):
    type: str = "journal"
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> JournalCheckin:
        if user_fact.kind != "journal":
            raise ValueError("UserFact kind must be 'journal'")

        return cls(
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class EnergyCheckin(BaseModel):
    type: str = "energy"
    level: int | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False) -> EnergyCheckin:
        if user_fact.kind != "energy-checkin":
            raise ValueError("UserFact kind must be 'energy-checkin'")

        # Extract level from options (format: "9/10" or just "9")
        level = None
        if data.get("options") and len(data["options"]) > 0:
            try:
                level_str = data["options"][0]
                if "/" in level_str:
                    level = int(level_str.split("/")[0])
                else:
                    level = int(level_str)
            except (ValueError, IndexError, TypeError):
                pass

        return cls(
            level=level,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class MovementCheckin(BaseModel):
    type: str = "movement"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    activity_type: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> MovementCheckin:
        if user_fact.kind != "movement-checkin":
            raise ValueError("UserFact kind must be 'movement-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        # Parse activity type from extraInfo
        activity_type = None
        if data.get("extraInfo"):
            try:
                extra_info = (
                    json.loads(data["extraInfo"]) if isinstance(data["extraInfo"], str) else data["extraInfo"]
                )
                activity_type = extra_info.get("activityType")
            except json.JSONDecodeError:
                pass

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            activity_type=activity_type,
            is_new=is_new,
        )


class DayMoodCheckin(BaseModel):
    type: str = "day_mood"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> DayMoodCheckin:
        if user_fact.kind != "day-mood-checkin":
            raise ValueError("UserFact kind must be 'day-mood-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class DoomscrollingCheckin(BaseModel):
    type: str = "doomscrolling"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    description: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> DoomscrollingCheckin:
        if user_fact.kind != "doom-scrolling-checkin":
            raise ValueError("UserFact kind must be 'doom-scrolling-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        # Parse description from extraInfo
        description = None
        if data.get("extraInfo"):
            try:
                extra_info = (
                    json.loads(data["extraInfo"]) if isinstance(data["extraInfo"], str) else data["extraInfo"]
                )
                description = extra_info.get("description")
            except json.JSONDecodeError:
                pass

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            description=description,
            is_new=is_new,
        )


class HabitCheckin(BaseModel):
    type: str = "habit"
    timestamp: datetime | None = None
    created_at: datetime | None = None
    value: str | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False) -> HabitCheckin:
        if user_fact.kind != "habits-routines-checkin":
            raise ValueError("UserFact kind must be 'habits-routines-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        return cls(
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            value=value,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class WaterCheckin(BaseModel):
    type: str = "water"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False) -> WaterCheckin:
        if user_fact.kind != "water-checkin":
            raise ValueError("UserFact kind must be 'water-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class SupplementsCheckin(BaseModel):
    type: str = "supplements"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> SupplementsCheckin:
        if user_fact.kind != "vitamins-supplements-checkin":
            raise ValueError("UserFact kind must be 'vitamins-supplements-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class AlcoholCheckin(BaseModel):
    type: str = "alcohol"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    had_binge: bool | None = None
    description: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> AlcoholCheckin:
        if user_fact.kind != "alcohol-checkin":
            raise ValueError("UserFact kind must be 'alcohol-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        # Parse binge info and description from extraInfo
        had_binge = None
        description = None
        if data.get("extraInfo"):
            try:
                extra_info = (
                    json.loads(data["extraInfo"]) if isinstance(data["extraInfo"], str) else data["extraInfo"]
                )
                had_binge_str = extra_info.get("hadBinge")
                had_binge = had_binge_str == "yes" if had_binge_str else None
                description = extra_info.get("description")
            except json.JSONDecodeError:
                pass

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            had_binge=had_binge,
            description=description,
            is_new=is_new,
        )


class CycleCheckin(BaseModel):
    type: str = "cycle"
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    cycle_length: int | None = None
    physical_symptoms: list[str] | None = None
    emotional_symptoms: list[str] | None = None
    behavioral_symptoms: list[str] | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False) -> CycleCheckin:
        if user_fact.kind != "cycle":
            raise ValueError("UserFact kind must be 'cycle'")

        # Parse data from nested options array
        period_start = None
        period_end = None
        cycle_length = None
        physical_symptoms = []
        emotional_symptoms = []
        behavioral_symptoms = []

        if data.get("options"):
            for option in data["options"]:
                if isinstance(option, list) and len(option) >= 2:
                    key, value = option[0], option[1]
                    if key == "dateStart":
                        try:
                            period_start = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                        except (ValueError, TypeError):
                            pass
                    elif key == "dateEnd":
                        try:
                            period_end = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                        except (ValueError, TypeError):
                            pass
                    elif key == "cycleLength":
                        cycle_length = int(value) if isinstance(value, (int, str)) else None
                    elif key == "physicalSymptoms" and isinstance(value, list):
                        physical_symptoms = value
                    elif key == "emotionalSymptoms" and isinstance(value, list):
                        emotional_symptoms = value
                    elif key == "behavioralSymptoms" and isinstance(value, list):
                        behavioral_symptoms = value

        return cls(
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            period_start=period_start,
            period_end=period_end,
            cycle_length=cycle_length,
            physical_symptoms=physical_symptoms if physical_symptoms else None,
            emotional_symptoms=emotional_symptoms if emotional_symptoms else None,
            behavioral_symptoms=behavioral_symptoms if behavioral_symptoms else None,
            is_new=is_new,
        )


class MentalRestCheckin(BaseModel):
    type: str = "mental_rest"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> MentalRestCheckin:
        if user_fact.kind != "mental-rest-checkin":
            raise ValueError("UserFact kind must be 'mental-rest-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


class SocialConnectionCheckin(BaseModel):
    type: str = "social_connection"
    value: str | None = None
    timestamp: datetime | None = None
    created_at: datetime | None = None
    note: str | None = None
    is_new: bool = False

    @classmethod
    def from_user_fact(
        cls, user_fact: UserFact, data: dict[str, Any], is_new: bool = False
    ) -> SocialConnectionCheckin:
        if user_fact.kind != "social-connection-checkin":
            raise ValueError("UserFact kind must be 'social-connection-checkin'")

        # Get value from options
        value = None
        if data.get("options") and len(data["options"]) > 0:
            value = data["options"][0]

        return cls(
            value=value,
            timestamp=datetime.fromisoformat(data.get("date", "").replace("Z", "+00:00"))
            if data.get("date")
            else None,
            created_at=user_fact.created_at,
            note=data.get("notes", ""),
            is_new=is_new,
        )


Checkin = (
    StressCheckin
    | SleepCheckin
    | EmotionCheckin
    | BingeEatingCheckin
    | FoodLogCheckin
    | EatingAttitudeTestCheckin
    | JournalCheckin
    | EnergyCheckin
    | MovementCheckin
    | DayMoodCheckin
    | DoomscrollingCheckin
    | HabitCheckin
    | WaterCheckin
    | SupplementsCheckin
    | AlcoholCheckin
    | CycleCheckin
    | MentalRestCheckin
    | SocialConnectionCheckin
)

CHECKIN_MAPPING = {
    "stress-checkin": StressCheckin,
    "sleep-checkin": SleepCheckin,
    "emotion-checkin": EmotionCheckin,
    "binge-eating": BingeEatingCheckin,
    "food-logging": FoodLogCheckin,
    "eat-9": EatingAttitudeTestCheckin,
    "eating_attitude": EatingAttitudeTestCheckin,
    "journal": JournalCheckin,
    "energy-checkin": EnergyCheckin,
    "movement-checkin": MovementCheckin,
    "day-mood-checkin": DayMoodCheckin,
    "doom-scrolling-checkin": DoomscrollingCheckin,
    "habits-routines-checkin": HabitCheckin,
    "water-checkin": WaterCheckin,
    "vitamins-supplements-checkin": SupplementsCheckin,
    "alcohol-checkin": AlcoholCheckin,
    "cycle": CycleCheckin,
    "mental-rest-checkin": MentalRestCheckin,
    "social-connection-checkin": SocialConnectionCheckin,
}

CHECKIN_NAMES = {k: v().type for k, v in CHECKIN_MAPPING.items()}


def parse_user_fact_to_checkin(user_fact: UserFact, last_message: datetime) -> Checkin | None:
    """Parse a UserFact into the appropriate checkin model based on its kind."""

    if user_fact.kind not in CHECKIN_MAPPING:
        return None

    checkin_class = CHECKIN_MAPPING[user_fact.kind]
    try:
        value_dict = json.loads(user_fact.value)
        if not isinstance(value_dict, dict):
            value_dict = {"value": user_fact.value}
        return checkin_class.from_user_fact(
            user_fact, value_dict, is_new=last_message is not None and user_fact.created_at > last_message
        )
    except ValueError:
        logger.warning("Failed to parse UserFact into %s", checkin_class.__name__, exc_info=True)
        return None


class UserInfo(BaseModel):
    id: str
    tz: str | None = None
    # app_day_start: str | None = None


class LLMDataSchema(BaseModel):
    schema_version: str = "1.2"
    user: UserInfo
    recent_checkins: list[Checkin]
    missing_checkins: list[str]
    risk_flags: dict[str, bool]
    intent_flags: dict[str, bool]

    @classmethod
    def create(cls, user: UserBase, fact: list[UserFact], last_message: datetime) -> LLMDataSchema:
        missing_checkins = [c for c in CHECKIN_MAPPING.keys()]
        for f in fact:
            if f.kind in missing_checkins:
                missing_checkins.remove(f.kind)
        return LLMDataSchema(
            user=UserInfo(
                id=str(user.id),
                tz=user.settings.timezone if user.settings and user.settings.timezone else None,
                app_day_start=(
                    user.settings.app_day_start if user.settings and user.settings.app_day_start else None
                ),
            ),
            recent_checkins=[
                parse_user_fact_to_checkin(f, last_message)
                for f in fact
                if parse_user_fact_to_checkin(f, last_message)
            ],
            missing_checkins=[CHECKIN_NAMES[checkin] for checkin in missing_checkins],
            risk_flags={risk: True for risk in (user.settings.risk_flags or [])},
            intent_flags={intent: True for intent in (user.settings.intent_flags or [])},
        )
