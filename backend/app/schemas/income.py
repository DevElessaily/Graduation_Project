from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime

class IncomeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    amount: Decimal = Field(gt=0)
    source: Optional[str] = Field(default=None, max_length=100)

class IncomeResponse(BaseModel):
    id: int
    title: str
    amount: str
    source: Optional[str] = None
    model_config = {"from_attributes": True}
