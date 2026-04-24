import json
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON, Column
from pydantic.json_schema import SkipJsonSchema

USER_FACT_KINDS = {
    "food-logging": "Food logging",
    "movement-checkin": "Movement check-in",
    "eat-9": "EAT-9",
    "social-connection-checkin": "Social connection check-in",
    "vomiting": "Vomiting",
    "meal_plan_response": "Meal plan response",
    "doom-scrolling-checkin": "Doom scrolling check-in",
    "binge-eating": "Binge eating",
    "vitamins-supplements-checkin": "Vitamins and supplements check-in",
    "mental-rest-checkin": "Mental rest check-in",
    "alcohol-checkin": "Alcohol check-in",
    "emotion-checkin": "Emotion check-in",
    "cycle": "Cycle",
    "habits-routines-checkin": "Habits and routines check-in",
    "stress-checkin": "Stress check-in",
    "water-checkin": "Water check-in",
    "meal_plan": "Meal plan",
    "day-mood-checkin": "Day mood check-in",
    "energy-checkin": "Energy check-in",
    "journal": "Journal",
    "sleep-checkin": "Sleep check-in",
    "eating_attitude": "Eating attitude",
    "sos-action": "SOS action",
}


def get_relative_time(d: datetime) -> str:
    """Convert a timestamp to a relative time string."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    diff = datetime.utcnow() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime("%d %b %y")
    elif diff.days == 1:
        return "1 day ago"
    elif diff.days > 1:
        return "{} days ago".format(diff.days)
    elif s <= 1:
        return "just now"
    elif s < 60:
        return "{} seconds ago".format(s)
    elif s < 120:
        return "1 minute ago"
    elif s < 3600:
        return "{} minutes ago".format(s / 60)
    elif s < 7200:
        return "1 hour ago"
    else:
        return "{} hours ago".format(s / 3600)


class UserFactBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    kind: str
    label: str
    value: str
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON))

    def get_checkin_label(self) -> str:
        """Get the label for the check-in."""
        return USER_FACT_KINDS.get(self.kind, self.kind.replace("_", " ").replace("-", " ").capitalize())

    def as_text(
        self,
        with_title: bool = False,
        with_notes: bool = True,
        with_timestamp: bool = True,
        with_relative_time: bool = False,
    ) -> str:
        """Convert user fact to readable string for chatbot context."""

        # Parse value if it's a string
        if isinstance(self.value, str):
            try:
                value_data = json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                value_data = {"raw": self.value}
        else:
            value_data = self.value or {}
        if not isinstance(value_data, dict):
            value_data = {"options": [value_data]}

        # Extract common fields
        options = value_data.get("options", [])
        options = [str(option).strip() for option in options if option]  # Clean up options
        notes = value_data.get("notes", "").strip()
        extra_info = value_data.get("extraInfo", "")

        # Parse extra_info if it's a JSON string
        parsed_extra = {}
        if extra_info:
            try:
                parsed_extra = json.loads(extra_info) if isinstance(extra_info, str) else extra_info
            except (json.JSONDecodeError, TypeError):
                pass

        # Format timestamp
        timestamp = self.created_at.strftime("%Y-%m-%d %H:%M")

        # Handle different kinds of facts
        if self.kind.startswith("eat-"):
            assessment_num = self.kind.split("-")[1] if "-" in self.kind else "unknown"
            result = f"EAT-{assessment_num} assessment" if with_title else ""
            if options:
                result += f": {', '.join(options)}"

        elif self.kind == "binge-eating":
            status = options[0] if options else "unknown"
            result = f"Binge eating: {status}" if with_title else f"{status}"
            if parsed_extra.get("intensity"):
                result += f" (intensity: {parsed_extra['intensity']})"

        elif self.kind == "vomiting":
            status = options[0] if options else "unknown"
            result = f"Vomiting: {status}" if with_title else f"{status}"
            if parsed_extra.get("intensity"):
                result += f" (intensity: {parsed_extra['intensity']})"

        elif self.kind == "food-logging":
            meal_type = options[0] if options else "meal"
            result = f"Food logging: {meal_type}" if with_title else f"{meal_type}"
            if parsed_extra.get("feeling"):
                result += f" (feeling: {parsed_extra['feeling']})"
            if parsed_extra.get("description"):
                result += f" - {parsed_extra['description']}"

        elif self.kind == "sleep-checkin":
            quality = options[0] if options else "unknown"
            result = f"Sleep quality: {quality}" if with_title else f"{quality}"

        elif self.kind == "doom-scrolling-checkin":
            status = options[0] if options else "unknown"
            result = f"Doom scrolling: {status}" if with_title else f"{status}"

        elif self.kind == "movement-checkin":
            status = options[0] if options else "unknown"
            result = f"Movement/exercise: {status}"
            if parsed_extra.get("activityType"):
                result += f" ({parsed_extra['activityType']})"

        elif self.kind == "emotion-checkin":
            emotion = options[0] if options else "unknown"
            result = f"Emotional state: {emotion}" if with_title else f"{emotion}"

        elif self.kind == "energy-checkin":
            level = options[0] if options else "unknown"
            result = f"Energy level: {level}" if with_title else f"{level}"

        elif self.kind == "stress-checkin":
            level = options[0] if options else "unknown"
            result = f"Stress level: {level}"

        elif self.kind == "habits-routines-checkin":
            habits = ", ".join(options) if options else "none specified"
            result = f"Habits/routines: {habits}" if with_title else f"{habits}"

        elif self.kind == "water-checkin":
            status = options[0] if options else "unknown"
            result = f"Water intake: {status}" if with_title else f"{status}"

        elif self.kind == "alcohol-checkin":
            status = options[0] if options else "unknown"
            result = f"Alcohol consumption: {status}" if with_title else f"{status}"

        elif self.kind == "sos-action":
            action = notes or "emergency action triggered"
            result = f"SOS Action: {action}" if with_title else f"{action}"

        else:
            # Generic fallback for unknown kinds
            result = f"{self.kind.replace('-', ' ').title()}" if with_title else ""
            if options:
                result += f": {', '.join(options)}"
            elif notes and with_notes:
                result += f": {notes[:50]}{'...' if len(notes) > 50 else ''}"

        # Add notes if present and not already included
        if with_notes and notes and not any(notes.lower() in result.lower() for notes in [notes]):
            # Truncate very long notes
            note_preview = notes[:100] + "..." if len(notes) > 100 else notes
            result += f" | Note: {note_preview}"

        # Add timestamp
        if with_timestamp:
            result += f" [{timestamp}]"
        elif with_relative_time:
            result += f" [{timestamp}]"
            # result += f" [{get_relative_time(self.created_at)}]"

        return result


class UserFactUpdate(UserFactBase):
    id: SkipJsonSchema[int] = Field(default=-1, exclude=True)
    user_id: SkipJsonSchema[int] = Field(default=-1, exclude=True)
    kind: str | None = None
    label: str | None = None
    value: str | None = None
    extra: dict | None = None


class UserFactCreate(UserFactBase):
    user_id: SkipJsonSchema[int] = Field(default=-1, exclude=True)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserFactRead(UserFactBase):
    id: int
    created_at: datetime
    updated_at: datetime
