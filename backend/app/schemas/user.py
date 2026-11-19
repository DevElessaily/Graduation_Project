
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class UserUpdate(BaseModel):
    Name: Optional[str] = None
    Email: Optional[EmailStr] = None
    Language: Optional[str] = None
    AlertViaEmail: Optional[bool] = None


class UserResponse(BaseModel):
    Id: int
    Name: str
    Email: str
    Language: Optional[str] = None
    AlertViaEmail: bool

    model_config = ConfigDict(from_attributes=True)
