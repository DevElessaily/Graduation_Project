from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.installment import Installment
from app.models.user import User

def get_or_create_user(db: Session, user_id: int = 1):
    user = db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user); db.flush()
    return user

def create_installment(db: Session, title: str, total_amount, monthly_amount, start_date, end_date=None, user_id: int = 1):
    user = get_or_create_user(db, user_id)
    inst = Installment(
        user_id=user.id, title=title, total_amount=total_amount,
        monthly_amount=monthly_amount, remaining_amount=total_amount,
        start_date=start_date, end_date=end_date,
    )
    db.add(inst); db.commit(); db.refresh(inst)
    return inst

def list_installments(db: Session, user_id: int = 1):
    return db.scalars(select(Installment).where(Installment.user_id == user_id)).all()

def delete_installment(db: Session, installment_id: int):
    inst = db.get(Installment, installment_id)
    if inst:
        db.delete(inst); db.commit()
    return inst
