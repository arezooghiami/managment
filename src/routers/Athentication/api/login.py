from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from DB.database import get_db, SessionLocal
from models.user import User

from schemas.user import UserRole
from passlib.context import CryptContext

router_login = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


TEMPLATES_DIR = "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router_login.get("/")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



@router_login.post("/login")
def login(
        request: Request,
        name: str = Form(...),
        code: str = Form(...),
        db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.code == code).first()
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "نام یا کد پرسنلی اشتباه است"},
            status_code=401,
        )
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["office_id"] = user.office_id  # اگر داری

    if user.role == 'admin':
        return RedirectResponse(url="/admin_dashboard", status_code=302)

    return RedirectResponse(url=f"/user_dashboard?user_id={user.id}", status_code=302)
