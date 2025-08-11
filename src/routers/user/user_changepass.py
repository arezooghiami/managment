from fastapi import APIRouter, Depends, Request, Form
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.user import User

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router_user.post("/change_password")
def change_password(
        request: Request,
        current_password: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter(User.id == user_id).first()

    # Check current password
    if not pwd_context.verify(current_password, user.password):
        request.session.setdefault("messageses", []).append("رمز عبور فعلی اشتباه است.")
        return RedirectResponse(url="/user_dashboard", status_code=302)

    # Check new passwords match
    if new_password != confirm_password:
        request.session.setdefault("messageses", []).append("رمز عبور جدید و تکرار آن یکسان نیست.")
        return RedirectResponse(url="/user_dashboard", status_code=302)

    # Update password
    hashed_new_password = pwd_context.hash(new_password)
    user.password = hashed_new_password
    db.commit()

    request.session.setdefault("messageses", []).append("رمز عبور با موفقیت تغییر کرد.")
    return RedirectResponse(url="/user_dashboard", status_code=302)
