from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.sms import SmsParseRequest, SmsFilterRequest, SmsBulkRequest
from app.services.sms_parser import parse_transaction_sms
from app.services.sms_service import store_sms, import_sms_transaction
from app.services.ml_classifier import get_classifier

router = APIRouter(prefix="/sms", tags=["SMS"])

@router.post("/parse")
def parse_sms(payload: SmsParseRequest):
    tx = parse_transaction_sms(payload.sender, payload.message)
    ml_verdict = None
    try:
        ml = get_classifier()
        r = ml.is_transaction(payload.message)
        if r is not None:
            ml_verdict = {"is_transaction": r[0], "score": r[1]}
    except Exception:
        pass
    if tx is None:
        is_tx = bool(ml_verdict["is_transaction"]) if ml_verdict else False
        return {"is_transaction": is_tx, "ml": ml_verdict, "transaction": None}
    return {"is_transaction": True, "ml": ml_verdict, "transaction": {
        "amount": str(tx.amount), "currency": tx.currency,
        "type": tx.db_type, "category": tx.category,
        "description": tx.description, "merchant": tx.merchant,
        "confidence": tx.confidence,
    }}

@router.post("/filter")
def filter_sms(payload: SmsFilterRequest, db: Session = Depends(get_db)):
    sms, created, outcome = store_sms(db, payload.sender, payload.message, payload.date)
    db.commit(); db.refresh(sms)
    return {"status": "received" if created else "duplicate",
            "id": sms.id, "transaction_created": outcome == "created"}

@router.post("/bulk")
def bulk_sms(payload: SmsBulkRequest, db: Session = Depends(get_db)):
    stored = skipped = created = 0
    for item in payload.items:
        _, is_new, outcome = store_sms(db, item.sender, item.message, item.date)
        stored += is_new; skipped += not is_new
        if outcome == "created": created += 1
    db.commit()
    return {"total": len(payload.items), "stored": stored,
            "skipped": skipped, "transactions_created": created}

@router.get("/history")
def sms_history(limit: int = 100, db: Session = Depends(get_db)):
    from sqlalchemy import select
    from app.models.sms import SmsMessage
    from app.models.transaction import Transaction
    from app.models.category import Category

    msgs = db.scalars(select(SmsMessage).order_by(SmsMessage.received_at.desc()).limit(limit)).all()
    refs = [f"sms:{m.id}" for m in msgs]
    txns = {}
    if refs:
        rows = db.execute(
            select(Transaction, Category)
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(Transaction.internal_reference.in_(refs))
        ).all()
        for t, c in rows:
            txns[t.internal_reference] = (t, c.name if c else "Other")

    result = []
    for m in msgs:
        linked = txns.get(f"sms:{m.id}")
        result.append({
            "id": m.id, "sender": m.sender, "message": m.message,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "transaction_id": linked[0].id if linked else None,
            "transaction_amount": str(linked[0].amount) if linked else None,
            "transaction_currency": linked[0].currency_code if linked else None,
            "transaction_category": linked[1] if linked else None,
        })
    return result