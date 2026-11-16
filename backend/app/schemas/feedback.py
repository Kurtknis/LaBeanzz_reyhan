from pydantic import BaseModel, Field
from typing import Literal, Optional

BrewContext = Literal["espresso", "filter", "milk"]

_RATING = {"ge": 1, "le": 5}


class CreateFeedbackRequest(BaseModel):
    overall:   int = Field(**_RATING)
    flavor:    int = Field(**_RATING)
    body:      int = Field(**_RATING)
    acidity:   int = Field(**_RATING)
    sweetness: int = Field(**_RATING)
    brew_context: BrewContext
    comment: Optional[str] = Field(None, max_length=2000)
