from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.income import IncomeCreate, IncomeResponse
from app.services.income_service import create_income, list_incomes, delete_income

router = APIRouter(prefix="/income", tags=["Income"])

@router.get("")
def get_incomes(db: Session = Depends(get_db)):
    return [{"id": i.id, "title": i.title, "amount": str(i.amount), "source": i.source} for i in list_incomes(db)]

@router.post("", status_code=201)
def add_income(payload: IncomeCreate, db: Session = Depends(get_db)):
    income = create_income(db, payload.title, payload.amount, payload.source)
    return {"id": income.id, "title": income.title, "amount": str(income.amount), "source": income.source}

@router.delete("/{income_id}")
def remove_income(income_id: int, db: Session = Depends(get_db)):
    if not delete_income(db, income_id):
        raise HTTPException(status_code=404, detail="Income not found")
    return {"status": "deleted", "id": income_id}
