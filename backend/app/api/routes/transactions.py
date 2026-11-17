from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.account_service import get_or_create_default_user_and_account

router = APIRouter(prefix="/transactions", tags=["Transactions"])

_TYPE_TO_DB = {"income": "deposit", "expense": "withdrawal", "transfer": "transfer"}
_DB_TO_TYPE = {"deposit": "income", "withdrawal": "expense", "transfer": "transfer"}


class TransactionCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    category: str = Field(min_length=1, max_length=100)
    type: Literal["income", "expense", "transfer"]
    description: str | None = Field(default=None, max_length=255)
    date: datetime | None = None


def _iso_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreateRequest, db: Session = Depends(get_db)):
    user, account = get_or_create_default_user_and_account(db)
    category_name = payload.category.strip() or "Other"
    category = db.scalar(select(Category).where(func.lower(Category.name) == category_name.lower()))
    if category is None:
        category = Category(name=category_name)
        db.add(category); db.flush()

    tx = Transaction(
        user_id=user.id, account_id=account.id,
        type=_TYPE_TO_DB[payload.type],
        amount=str(payload.amount),
        currency_code=account.currency_code or "EGP",
        transaction_date=payload.date or datetime.now(timezone.utc),
        description=payload.description or category_name,
        category_id=category.id, source="manual",
    )
    db.add(tx); db.flush()
    db.commit(); db.refresh(tx)
    return {"status": "created", "id": tx.id, "amount": str(tx.amount),
            "category": category.name, "type": payload.type,
            "description": tx.description, "date": _iso_utc(tx.transaction_date),
            "currency": tx.currency_code}


@router.get("")
def list_transactions(limit: int = 50, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    rows = db.execute(
        select(Transaction, Category)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(limit)
    ).all()
    return [{"id": t.id, "amount": str(t.amount),
             "type": _DB_TO_TYPE.get(t.type, t.type),
             "category": c.name if c else "Other",
             "description": t.description, "date": _iso_utc(t.transaction_date),
             "currency": t.currency_code, "source": t.source}
            for t, c in rows]


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = db.get(Transaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx); db.commit()
    return {"status": "deleted", "id": transaction_id}
