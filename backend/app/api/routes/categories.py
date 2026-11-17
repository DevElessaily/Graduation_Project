from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.models.transaction import Transaction

router = APIRouter(prefix="/categories", tags=["Categories"])


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name} for c in db.scalars(select(Category)).all()]


@router.post("", status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.scalar(select(Category).where(Category.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Category already exists")
    cat = Category(name=payload.name)
    db.add(cat); db.commit(); db.refresh(cat)
    return {"id": cat.id, "name": cat.name}


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if db.scalar(select(Transaction.id).where(Transaction.category_id == category_id).limit(1)):
        raise HTTPException(status_code=409, detail="Category is used by transactions")
    db.delete(cat); db.commit()
    return {"status": "deleted", "id": category_id}
