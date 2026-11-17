from sqlalchemy.orm import Session
from app.models.user import User
from app.models.account import Account

def get_or_create_default_user_and_account(db: Session):
    user = db.get(User, 1)
    if user is None:
        user = User(id=1)
        db.add(user); db.flush()
    account = db.get(Account, 1)
    if account is None:
        account = Account(id=1, user_id=user.id)
        db.add(account); db.flush()
    return user, account