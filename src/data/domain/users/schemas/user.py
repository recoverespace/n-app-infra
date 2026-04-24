from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.json_schema import SkipJsonSchema
from sqlmodel import Column, Field, SQLModel

from data.lib.model import pydantic_column_type


class UserPaymentStatus(StrEnum):
    free = "free"
    paid = "paid"
    trial = "trial"
    promo = "promo"


class UserLanguage(StrEnum):
    english = "en"


class UserSettingsModel(BaseModel):
    age: int | None = 20
    gender: str | None = ""
    height_cm: int | None = 160
    lastEatTestDate: datetime | None = None
    is_onboarding_finished: bool = False
    is_paywall_onboarding_finished: bool = False
    has_watched_meal_plan_video: bool = False
    last_meal_planning_date: datetime | None = None
    last_meal_planning_check_date: datetime | None = None
    last_insight_date: datetime | None = None
    current_meal_plan_video: int = 0
    meal_plan_counter: int = 0
    meal_plan_cheer_index: int = 0
    notifications_enabled: bool = False
    questions_answers: dict[str, str | None] = Field(default_factory=dict)
    weight_kg: int | None = 132
    is_migrated_user: bool = False
    user_source: str | None = None
    timezone: str | None = None
    app_day_start: str | None = None
    risk_flags: list[str] | None = None
    intent_flags: list[str] | None = None
    goals: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    def __str__(self) -> str:
        return self.model_dump_json(indent=2)

    def as_text(self) -> str:
        parts = []

        # Basic demographics
        # if self.age:
        #     parts.append(f"Age: {self.age}")

        # if self.gender and self.gender.strip():
        #     parts.append(f"Gender: {self.gender}")

        # # Physical attributes
        # if self.height_cm:
        #     parts.append(f"Height: {self.height_cm} cm")

        # if self.weight_kg:
        #     parts.append(f"Weight: {self.weight_kg} kg")

        # Assessment history
        if self.lastEatTestDate:
            last_test = self.lastEatTestDate.strftime("%Y-%m-%d")
            parts.append(f"Last eating assessment: {last_test}")

        # Questions/answers context (only if there are meaningful answers)
        # meaningful_qa = {
        #     k: v for k, v in self.questions_answers.items() if v and str(v).strip() and str(v).strip().lower() not in ["", "none", "null"]
        # }

        # if meaningful_qa:
        #     qa_summary = []
        #     for question, answer in meaningful_qa.items():
        #         # Clean up question key for readability
        #         clean_question = question.replace("_", " ").replace("-", " ").title()
        #         qa_summary.append(f"{clean_question}: {answer}")

        #     if qa_summary:
        #         parts.append(f"Profile details: {'; '.join(qa_summary)}")

        return " | ".join(parts) if parts else ""


class UserSettingsCreate(BaseModel):
    age: int | None = 20
    gender: str | None = ""
    height_cm: int | None = 160
    lastEatTestDate: datetime | None = None
    is_onboarding_finished: bool = False
    is_paywall_onboarding_finished: bool = False
    has_watched_meal_plan_video: bool = False
    last_meal_planning_date: datetime | None = None
    last_meal_planning_check_date: datetime | None = None
    last_insight_date: datetime | None = None
    current_meal_plan_video: int = 0
    meal_plan_counter: int = 0
    meal_plan_cheer_index: int = 0
    notifications_enabled: bool = False
    questions_answers: dict[str, str | None] = Field(default_factory=dict)
    weight_kg: int | None = 132
    is_migrated_user: bool = False
    user_source: str | None = None
    timezone: str | None = None
    app_day_start: str | None = None
    risk_flags: list[str] | None = None
    intent_flags: list[str] | None = None
    goals: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="ignore", missing="ignore")  # type: ignore


class UserBase(SQLModel):
    uid: str = Field(index=True, title="UID", description="Unique identifier for the user")
    email: str | None = None
    is_active: bool = True
    is_deleted: bool = False
    first_name: str | None = Field(default="", title="First Name")
    last_name: str | None = None
    avatar_url: str | None = None
    display_name: str | None = None
    stripe_id: str | None = None
    tenant_id: int | None = None
    payment_status: str | None = "free"
    settings: UserSettingsModel = Field(
        default_factory=UserSettingsModel, sa_column=Column(pydantic_column_type(UserSettingsModel))
    )

    def __str__(self) -> str:
        name = self.display_name or " ".join([self.first_name or "", self.last_name or ""])
        return f"{name} ({self.email}) [{self.uid}]"


class UserCreate(UserBase): ...


class UserUpdate(UserBase):
    id: SkipJsonSchema[int] = Field(default=-1, exclude=True)
    uid: SkipJsonSchema[str] = Field(default="", exclude=True)
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    display_name: str | None = None
    stripe_id: SkipJsonSchema[str | None] = Field(default=None, exclude=True)
    payment_status: SkipJsonSchema[UserPaymentStatus] = Field(default="free", exclude=True)
    pass


class UserRead(UserBase):
    id: int
    settings: UserSettingsModel = Field(default_factory=UserSettingsModel)
    created_at: datetime
