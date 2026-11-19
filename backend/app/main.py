from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa
Base.metadata.create_all(bind=engine)

from app.api.routes import sms, transactions, categories, income, installment
app = FastAPI(title="Financial Coach")
app.include_router(sms.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(installment.router, prefix="/api")
