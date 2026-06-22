import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from backend.models.database import get_db
from backend.models.models import MenuItem, Category, User
from backend.schemas.schemas import MenuItemCreate, MenuItemUpdate, MenuItemOut, CategoryCreate, CategoryOut
from backend.utils.auth import get_current_user, require_staff_or_above, require_admin_or_manager
from backend.config import settings

router = APIRouter(prefix="/menu", tags=["Menu"])


# ─── Categories ──────────────────────────────

@router.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).filter(Category.is_active == True).order_by(Category.display_order).all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/categories/{cat_id}", response_model=CategoryOut)
def update_category(
    cat_id: int,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    cat.is_active = False
    db.commit()


# ─── Menu Items ──────────────────────────────

@router.get("/items", response_model=List[MenuItemOut])
def list_items(
    category_id: Optional[int] = None,
    is_vegetarian: Optional[bool] = None,
    available_only: bool = True,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(MenuItem).options(joinedload(MenuItem.category))
    if available_only:
        q = q.filter(MenuItem.is_available == True)
    if category_id:
        q = q.filter(MenuItem.category_id == category_id)
    if is_vegetarian is not None:
        q = q.filter(MenuItem.is_vegetarian == is_vegetarian)
    if search:
        q = q.filter(MenuItem.name.ilike(f"%{search}%"))
    return q.all()


@router.get("/items/{item_id}", response_model=MenuItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).options(joinedload(MenuItem.category)).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.post("/items", response_model=MenuItemOut, status_code=201)
def create_item(
    data: MenuItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    if not db.query(Category).filter(Category.id == data.category_id).first():
        raise HTTPException(400, "Category not found")
    item = MenuItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=MenuItemOut)
def update_item(
    item_id: int,
    data: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    item.is_available = False
    db.commit()


@router.post("/items/{item_id}/image")
async def upload_item_image(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager),
):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")

    ext = file.filename.split(".")[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        raise HTTPException(400, "Only JPG/PNG/WEBP allowed")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"menu_{item_id}.{ext}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    item.image_url = f"/static/images/uploads/{filename}"
    db.commit()
    return {"image_url": item.image_url}