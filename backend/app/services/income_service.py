from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.income import Income
from app.models.user import User

def get_or_create_user(db: Session, user_id: int = 1):
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user); db.flush()
    return user

def create_income(db: Session, title: str, amount, source=None, user_id: int = 1):
    user = get_or_create_user(db, user_id)
    income = Income(user_id=user.id, title=title, amount=amount, source=source)
    db.add(income); db.commit(); db.refresh(income)
    return income

def list_incomes(db: Session, user_id: int = 1):
    return db.scalars(select(Income).where(Income.user_id == user_id)).all()

def delete_income(db: Session, income_id: int):
    income = db.get(Income, income_id)
    if income:
        db.delete(income); db.commit()
    return income
