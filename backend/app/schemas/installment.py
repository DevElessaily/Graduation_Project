from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import date

class InstallmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    total_amount: Decimal = Field(gt=0)
    monthly_amount: Decimal = Field(gt=0)
    start_date: date
    end_date: Optional[date] = None

class InstallmentResponse(BaseModel):
    id: int
    title: str
    total_amount: str
    monthly_amount: str
    remaining_amount: str
    start_date: date
    end_date: Optional[date] = None
    model_config = {"from_attributes": True}
