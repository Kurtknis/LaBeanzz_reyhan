"""Pydantic schemas for AI endpoints."""
from __future__ import annotations
import uuid
from typing import Literal
from pydantic import BaseModel, field_validator, model_validator


class GenerateBlendRequest(BaseModel):
    prompt: str
    style: Literal["espresso", "filter", "milk"] = "espresso"
    preset_id: str | None = None
    max_price_per_kg: float | None = None

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("prompt must not be empty")
        if len(v) > 1000:
            raise ValueError("prompt must be 1000 characters or fewer")
        return v


class SubstituteRequest(BaseModel):
    blend_id: uuid.UUID
    # Omit to replace every bean in the blend that is currently unavailable
    missing_bean_id: uuid.UUID | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def content_bounds(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        if len(v) > 2000:
            raise ValueError("message must be 2000 characters or fewer")
        return v


class ChatRequest(BaseModel):
    messages: list[ChatMessage]

    @model_validator(mode="after")
    def ends_with_user_turn(self) -> "ChatRequest":
        if not self.messages:
            raise ValueError("messages must not be empty")
        if self.messages[-1].role != "user":
            raise ValueError("the last message must come from the user")
        if len(self.messages) > 20:
            raise ValueError("a conversation can have at most 20 messages")
        return self


class RecipeItem(BaseModel):
    coffee_bean_id: str
    percentage: int

    @field_validator("percentage")
    @classmethod
    def pct_range(cls, v: int) -> int:
        if not (5 <= v <= 85):
            raise ValueError("percentage must be between 5 and 85")
        return v


class LLMBlendOutput(BaseModel):
    blend_name: str
    description: str
    recipe: list[RecipeItem]
    reasoning: str
    applied_feedback: list[str]

    @model_validator(mode="after")
    def validate_recipe(self) -> "LLMBlendOutput":
        if not (2 <= len(self.recipe) <= 5):
            raise ValueError(f"recipe must have 2–5 items, got {len(self.recipe)}")
        ids = [r.coffee_bean_id for r in self.recipe]
        if len(ids) != len(set(ids)):
            raise ValueError("recipe contains duplicate beans")
        total = sum(r.percentage for r in self.recipe)
        if total != 100:
            raise ValueError(f"percentages must sum to 100, got {total}")
        if not (3 <= len(self.blend_name) <= 60):
            raise ValueError("blend_name must be 3–60 characters")
        if not (10 <= len(self.description) <= 300):
            raise ValueError("description must be 10–300 characters")
        if len(self.reasoning) > 1000:
            raise ValueError("reasoning must be 1000 characters or fewer")
        if len(self.applied_feedback) > 5:
            raise ValueError("applied_feedback must have at most 5 items")
        return self
