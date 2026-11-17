from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.sms import SmsMessage
from app.models.transaction import Transaction
from app.services.sms_parser import parse_transaction_sms
from app.services.account_service import get_or_create_default_user_and_account

def _received_at(epoch):
    if epoch is None:
        return datetime.now(timezone.utc)
    if epoch > 10_000_000_000:
        epoch //= 1000
    try:
        return datetime.fromtimestamp(epoch, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return datetime.now(timezone.utc)

def _get_or_create_category(db, name):
    from app.models.category import Category
    from sqlalchemy import func
    cat = db.scalar(select(Category).where(func.lower(Category.name) == name.lower()))
    if cat is None:
        cat = Category(name=name)
        db.add(cat); db.flush()
    return cat

def import_sms_transaction(db: Session, sms: SmsMessage) -> str:
    try:
        reference = f"sms:{sms.id}"
        existing = db.scalar(select(Transaction).where(Transaction.internal_reference == reference))
        if existing is not None:
            return "exists"

        parsed = parse_transaction_sms(sms.sender, sms.message)
        if parsed is None:
            return "ignored"

        user, account = get_or_create_default_user_and_account(db)
        category = _get_or_create_category(db, parsed.category)
        occurred_at = sms.received_at or datetime.now(timezone.utc)

        # dedupe within 30 min
        from datetime import timedelta
        dup = db.scalar(select(Transaction).where(
            Transaction.source == "sms",
            Transaction.type == parsed.db_type,
            Transaction.amount == str(parsed.amount),
            Transaction.category_id == category.id,
            Transaction.transaction_date >= occurred_at - timedelta(minutes=30),
            Transaction.transaction_date <= occurred_at + timedelta(minutes=30),
        ))
        if dup is not None:
            return "duplicate"

        with db.begin_nested():
            tx = Transaction(
                user_id=user.id, account_id=account.id,
                type=parsed.db_type, amount=str(parsed.amount),
                currency_code=parsed.currency or "EGP",
                transaction_date=occurred_at,
                description=parsed.description,
                category_id=category.id,
                merchant=parsed.merchant,
                internal_reference=reference, source="sms",
            )
            db.add(tx); db.flush()
        return "created"
    except Exception:
        return "failed"

def store_sms(db: Session, sender: str, message: str, date=None):
    received_at = _received_at(date)
    existing = db.scalar(select(SmsMessage).where(
        SmsMessage.sender == sender,
        SmsMessage.message == message,
        SmsMessage.received_at == received_at,
    ))
    if existing is not None:
        return existing, False, import_sms_transaction(db, existing)
    sms = SmsMessage(sender=sender, message=message, received_at=received_at)
    db.add(sms); db.flush()
    return sms, True, import_sms_transaction(db, sms)