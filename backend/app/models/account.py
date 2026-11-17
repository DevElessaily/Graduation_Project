from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(150), nullable=False, default="Main Account")
    currency_code = Column(String(10), nullable=False, default="EGP")
    balance = Column(String(50), nullable=False, default="0")