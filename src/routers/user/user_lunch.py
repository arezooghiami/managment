from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from DB.database import get_db
from models.user import User
from models.lunch import LunchMenu, LunchOrder

from starlette.templating import Jinja2Templates

router_user_lunch = APIRouter()
templates = Jinja2Templates(directory="templates")
from datetime import datetime, time


@router_user_lunch.get("/user_dashboard/lunch")
async def user_lunch(request: Request, user_id: int, db: Session = Depends(get_db)):
    # Fetch user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now()
    cutoff_time = time(10, 0)
    today = date.today()
    tomorrow = today + timedelta(days=1)

    menus = []
    orders = []
    user_order_today = None
    user_order_tomorrow = None

    if now.time() < cutoff_time:
        # Before 10 AM: Show today's and tomorrow's menus
        menu_today = db.query(LunchMenu).filter(LunchMenu.date == today).first()
        menu_tomorrow = db.query(LunchMenu).filter(LunchMenu.date == tomorrow).first()
        menus.extend([menu for menu in [menu_today, menu_tomorrow] if menu])

        orders_today = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == today
        ).all()
        orders_tomorrow = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == tomorrow
        ).all()
        orders.extend(orders_today + orders_tomorrow)

        user_order_today = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == today
        ).first()
        user_order_tomorrow = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == tomorrow
        ).first()
    else:
        # After 10 AM: Show only tomorrow's menu
        menu_tomorrow = db.query(LunchMenu).filter(LunchMenu.date == tomorrow).first()
        if menu_tomorrow:
            menus.append(menu_tomorrow)

        orders = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == tomorrow
        ).all()
        user_order_tomorrow = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == tomorrow
        ).first()

    # Add message if no orders or menus are available
    if not menus:
        request.session.setdefault("messages", []).append("منویی برای نمایش وجود ندارد.")
    if not orders:
        request.session.setdefault("messages", []).append("سفارشی برای ناهار ثبت نشده است.")

    return templates.TemplateResponse("user/lunch.html", {
        "request": request,
        "user": user,
        "lunch_menu": menus,
        "orders": orders,
        "user_order_today": user_order_today,
        "user_order_tomorrow": user_order_tomorrow,
        "now": now,
        "cutoff_time": cutoff_time
    })
