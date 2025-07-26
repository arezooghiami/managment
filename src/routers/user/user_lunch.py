from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from starlette.responses import RedirectResponse

from DB.database import get_db
from models.user import User
from models.lunch import LunchMenu, LunchOrder

from starlette.templating import Jinja2Templates

router_user_lunch = APIRouter()
templates = Jinja2Templates(directory="templates")
from datetime import datetime, time


@router_user_lunch.get("/user_dashboard/lunch")
async def user_lunch(request: Request,  db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)
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

@router_user_lunch.post("/order_lunch")
def order_lunch(
        request: Request,
        user_id: int = Form(...),
        menu_id: int = Form(...),
        selected_dish: str = Form(...),
        for_guest: Optional[str] = Form(None),
        guest_name: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    # order_date = date.today() + timedelta(days=1)
    now = datetime.now()
    cutoff_time = time(10, 0)

    # منطق بررسی زمان برای سفارش امروز یا فردا
    if now.time() < cutoff_time:
        order_date = date.today()
    else:
        order_date = date.today() + timedelta(days=1)


    if for_guest == "on" and guest_name:
        # سفارش جدید برای مهمان
        new_order = LunchOrder(
            user_id=user_id,
            lunch_menu_id=menu_id,
            selected_dish=selected_dish,
            order_date=order_date,
            guest_name=guest_name
        )
        db.add(new_order)
        message = f"سفارش برای مهمان {guest_name} ثبت شد."
    else:
        # فقط یک سفارش در روز برای خود شخص قابل ویرایش است
        existing_order = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == order_date,
            LunchOrder.guest_name == None
        ).first()

        if existing_order:
            existing_order.lunch_menu_id = menu_id
            existing_order.selected_dish = selected_dish
            message = "سفارش ناهار شما ویرایش شد."
        else:
            new_order = LunchOrder(
                user_id=user_id,
                lunch_menu_id=menu_id,
                selected_dish=selected_dish,
                order_date=order_date
            )
            db.add(new_order)
            message = "سفارش ناهار شما ثبت شد."

    db.commit()
    if for_guest == "on" and guest_name:

        message = f"سفارش ناهار برای مهمان «{guest_name}» با موفقیت ثبت شد."
    else:

        message = "سفارش ناهار شما با موفقیت ثبت شد."

    if "messages" not in request.session:
        request.session["messages"] = []

    request.session["messages"].append(message)
    return RedirectResponse(url=f"/user_dashboard/lunch", status_code=302)
