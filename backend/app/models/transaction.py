from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    type = Column(String(50), nullable=False)          # withdrawal / deposit
    amount = Column(String(50), nullable=False)
    currency_code = Column(String(10), nullable=False, default="EGP")
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    description = Column(String(255), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    merchant = Column(String(255), nullable=True)
    sms_id = Column(Integer, ForeignKey("sms_messages.id"), nullable=True, unique=True)
    internal_reference = Column(String(100), unique=True, nullable=True)  # "sms:<id>"
    source = Column(String(50), nullable=False, default="sms")

    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    sms = relationship("SmsMessage", back_populates="transaction")