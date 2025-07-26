from fastapi import APIRouter, Depends, Request

from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from starlette.responses import RedirectResponse

from DB.database import get_db
from models.meet import MeetingRoomReservation
from models.user import User
from models.lunch import LunchMenu, LunchOrder

from starlette.templating import Jinja2Templates

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")

@router_user.get("/user_dashboard")
def user_dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    tomorrow = date.today() + timedelta(days=1)

    lunch_menu = db.query(LunchMenu).filter(LunchMenu.date == tomorrow).first()
    user_order = db.query(LunchOrder).filter(
        LunchOrder.user_id == user_id,
        LunchOrder.order_date == tomorrow
    ).first()

    # meetings = db.query(MeetingRoomReservation).all()
    # reserv = db.query(User).filter(meetings.user_id==User.id)
    meetings = db.query(MeetingRoomReservation).options(joinedload(MeetingRoomReservation.user)).all()
    orders = db.query(LunchOrder).filter(
        LunchOrder.user_id == user_id,
        LunchOrder.order_date == tomorrow
    ).all()
    if not orders:
        request.session.setdefault("messages", []).append("سفارشی برای ناهار فردا ثبت نشده است.")

    return templates.TemplateResponse("user/user_dashboard.html", {
        "request": request,
        "user": user,
        "order": orders,
        "lunch_menu": lunch_menu,
        "user_order": user_order,
        "meetings": meetings,
        "today": date.today()
    })
