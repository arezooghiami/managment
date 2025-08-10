from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session

from DB.database import get_db
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin_dashboard")
def admin_dashboard(request: Request,db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    return templates.TemplateResponse("admin/admin_dashboard.html", {
        "request": request,
        "name":user.name + user.family,


    })
