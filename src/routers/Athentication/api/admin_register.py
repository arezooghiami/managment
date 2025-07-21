from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from routers.Athentication.user_services import create_user, get_all_users, update_user, delete_user
from schemas.user import UserCreate, UserRead

from DB.database import get_db
from typing import List

router_admin = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


@router_admin.get("/", response_model=List[UserRead])
def list_users(db: Session = Depends(get_db)):
    return get_all_users(db)


@router_admin.post("/", response_model=UserRead)
def add_user(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)


@router_admin.put("/{user_id}", response_model=UserRead)
def edit_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    updated = update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return updated


@router_admin.delete("/{user_id}")
def delete_user_route(user_id: int, db: Session = Depends(get_db)):
    deleted = delete_user(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    return {"message": "کاربر حذف شد"}
