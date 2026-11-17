from pydantic import BaseModel, Field

class SmsParseRequest(BaseModel):
    sender: str
    message: str

class SmsFilterRequest(BaseModel):
    sender: str = Field(min_length=1)
    message: str = Field(min_length=1)
    date: int | None = None

class SmsBulkRequest(BaseModel):
    items: list[SmsFilterRequest] = Field(default_factory=list)