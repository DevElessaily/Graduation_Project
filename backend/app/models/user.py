from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, default="Local User")
    email = Column(String(255), unique=True, nullable=False, default="local@app")
    password = Column(String(255), nullable=False, default="")
