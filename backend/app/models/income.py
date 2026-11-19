from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Income(Base):
    __tablename__ = "incomes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    source = Column(String(100), nullable=True)

    user = relationship("User", back_populates="incomes")
