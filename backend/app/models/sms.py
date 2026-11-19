from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base

class SmsMessage(Base):
    __tablename__ = "sms_messages"
    id = Column(Integer, primary_key=True)
    sender = Column(String(255), nullable=False, index=True)
    message = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transaction = relationship("Transaction", back_populates="sms", uselist=False)