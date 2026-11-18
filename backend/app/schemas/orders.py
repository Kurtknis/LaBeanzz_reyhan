import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

OrderStatus = Literal[
    "PENDING", "CONFIRMED", "PREPARING", "READY",
    "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED",
]

_KG = dict(gt=Decimal("0"), max_digits=10, decimal_places=2)


class OrderLineInput(BaseModel):
    coffee_bean_id: uuid.UUID
    quantity_kg: Decimal = Field(**_KG)


class CreateOrderRequest(BaseModel):
    items: list[OrderLineInput] = Field(min_length=1, max_length=20)
    source_blend_id: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def no_duplicate_beans(self) -> "CreateOrderRequest":
        ids = [i.coffee_bean_id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each bean can appear only once per order.")
        return self


class ReorderBlendRequest(BaseModel):
    total_kg: Decimal = Field(ge=Decimal("1"), max_digits=10, decimal_places=2)


class OrderStatusRequest(BaseModel):
    status: OrderStatus
    eta_date: Optional[date] = None


class OwnerStockRequest(BaseModel):
    coffee_bean_id: uuid.UUID
    quantity_kg: Decimal = Field(ge=Decimal("0"), max_digits=10, decimal_places=2)
