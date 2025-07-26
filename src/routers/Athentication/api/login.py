from fastapi import APIRouter, Depends, Request, Form
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.user import User

router_login = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEMPLATES_DIR = "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router_login.get("/")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router_login.post("/login")
async def login(
        request: Request,
        code: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.code == code).first()
    if not user or not pwd_context.verify(password, user.password) or user.status == "deactive":
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "نام کاربری یا رمز عبور اشتباه است"},
        )

    # ذخیره اطلاعات حیاتی در session (اما نه نمایش در URL)
    request.session["user_id"] = user.id
    request.session["role"] = user.role
    request.session["office_id"] = user.office_id

    if user.role == 'admin':
        return RedirectResponse(url="/admin_dashboard", status_code=302)
    else:
        return RedirectResponse(url="/user_dashboard", status_code=302)
