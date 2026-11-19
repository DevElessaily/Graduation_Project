from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.installment import InstallmentCreate, InstallmentResponse
from app.services.installment_service import create_installment, list_installments, delete_installment

router = APIRouter(prefix="/installments", tags=["Installments"])

@router.get("")
def get_installments(db: Session = Depends(get_db)):
    return [{"id": i.id, "title": i.title, "total_amount": str(i.total_amount),
             "monthly_amount": str(i.monthly_amount), "remaining_amount": str(i.remaining_amount),
             "start_date": i.start_date.isoformat(), "end_date": i.end_date.isoformat() if i.end_date else None}
            for i in list_installments(db)]

@router.post("", status_code=201)
def add_installment(payload: InstallmentCreate, db: Session = Depends(get_db)):
    inst = create_installment(db, payload.title, payload.total_amount, payload.monthly_amount,
                              payload.start_date, payload.end_date)
    return {"id": inst.id, "title": inst.title, "total_amount": str(inst.total_amount),
            "monthly_amount": str(inst.monthly_amount), "remaining_amount": str(inst.remaining_amount),
            "start_date": inst.start_date.isoformat(), "end_date": inst.end_date.isoformat() if inst.end_date else None}

@router.delete("/{installment_id}")
def remove_installment(installment_id: int, db: Session = Depends(get_db)):
    if not delete_installment(db, installment_id):
        raise HTTPException(status_code=404, detail="Installment not found")
    return {"status": "deleted", "id": installment_id}
