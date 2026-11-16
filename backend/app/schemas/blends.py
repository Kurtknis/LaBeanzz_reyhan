from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional
from decimal import Decimal

BlendStatus = Literal["DRAFT", "ACTIVE", "ARCHIVED"]
BlendStyle = Literal["espresso", "filter", "milk"]


# ─── Blend item (recipe component) ───────────────────────────────────────────

class BlendItemInput(BaseModel):
    coffee_bean_id: str = Field(min_length=36, max_length=36)
    percentage: int = Field(ge=1, le=100)


# ─── Create blend ─────────────────────────────────────────────────────────────

class CreateBlendRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    style: Optional[BlendStyle] = None
    items: list[BlendItemInput] = Field(min_length=2, max_length=5)
    source_generation_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_recipe(self) -> "CreateBlendRequest":
        total = sum(i.percentage for i in self.items)
        if total != 100:
            raise ValueError(f"Recipe percentages must sum to 100, got {total}.")
        ids = [i.coffee_bean_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Recipe contains duplicate beans.")
        return self


# ─── Patch blend ──────────────────────────────────────────────────────────────

class PatchBlendRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    style: Optional[BlendStyle] = None
    items: Optional[list[BlendItemInput]] = Field(None, min_length=2, max_length=5)

    @model_validator(mode="after")
    def validate_recipe(self) -> "PatchBlendRequest":
        if self.items is not None:
            total = sum(i.percentage for i in self.items)
            if total != 100:
                raise ValueError(f"Recipe percentages must sum to 100, got {total}.")
            ids = [i.coffee_bean_id for i in self.items]
            if len(ids) != len(set(ids)):
                raise ValueError("Recipe contains duplicate beans.")
        return self


# ─── Status transition ────────────────────────────────────────────────────────

class BlendStatusRequest(BaseModel):
    status: BlendStatus
    daily_usage_kg: Optional[Decimal] = Field(None, gt=Decimal("0"))

    @model_validator(mode="after")
    def daily_usage_required_for_active(self) -> "BlendStatusRequest":
        if self.status == "ACTIVE" and self.daily_usage_kg is None:
            raise ValueError("daily_usage_kg is required when activating a blend.")
        return self


# ─── Presets ──────────────────────────────────────────────────────────────────

class CreatePresetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    flavor_preferences: dict = Field(default_factory=dict)
    acidity_pref: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("10"))
    body_pref: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("10"))
    sweetness_pref: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("10"))
    brewing_method: Optional[str] = Field(None, max_length=50)
    coffee_style: Optional[BlendStyle] = None
    notes: Optional[str] = Field(None, max_length=2000)


class PatchPresetRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    flavor_preferences: Optional[dict] = None
    acidity_pref: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("10"))
    body_pref: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("10"))
    sweetness_pref: Optional[Decimal] = Field(None, ge=Decimal("0"), le=Decimal("10"))
    brewing_method: Optional[str] = Field(None, max_length=50)
    coffee_style: Optional[BlendStyle] = None
    notes: Optional[str] = Field(None, max_length=2000)
