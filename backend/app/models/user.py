from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, default="Local User")
    email = Column(String(255), unique=True, nullable=False, default="local@app")
    password = Column(String(255), nullable=False, default="")

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    incomes = relationship("Income", back_populates="user", cascade="all, delete-orphan")
    installments = relationship("Installment", back_populates="user", cascade="all, delete-orphan")
