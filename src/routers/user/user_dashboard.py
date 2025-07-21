from typing import Optional

from fastapi import APIRouter, Depends, Request, Form,HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from DB.database import get_db
from models.meet import MeetingRoomReservation
from models.user import User
from models.lunch import LunchMenu, LunchOrder

from starlette.templating import Jinja2Templates

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")


@router_user.get("/user_dashboard")
def user_dashboard(request: Request, user_id: int, db: Session = Depends(get_db)):
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

@router_user.post("/order_lunch")
def order_lunch(
        request: Request,
        user_id: int = Form(...),
        menu_id: int = Form(...),
        selected_dish: str = Form(...),
        for_guest: Optional[str] = Form(None),
        guest_name: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
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
    return RedirectResponse(url=f"/user_dashboard?user_id={user_id}", status_code=302)

# @router_user.post("/order_lunch")
# def order_lunch(
#         request: Request,
#         user_id: int = Form(...),
#         menu_id: int = Form(...),
#         selected_dish: str = Form(...),
#         db: Session = Depends(get_db)
# ):
#     order_date = date.today() + timedelta(days=1)
#
#     existing_order = db.query(LunchOrder).filter(
#         LunchOrder.user_id == user_id,
#         LunchOrder.order_date == order_date
#     ).first()
#
#     if existing_order:
#         existing_order.lunch_menu_id = menu_id
#         existing_order.selected_dish = selected_dish
#     else:
#         new_order = LunchOrder(
#             user_id=user_id,
#             lunch_menu_id=menu_id,
#             selected_dish=selected_dish,
#             order_date=order_date
#         )
#         db.add(new_order)
#
#     db.commit()
#     request.session["message"] = "سفارش ناهار شما با موفقیت ثبت شد."
#     return RedirectResponse(url=f"/user_dashboard?user_id={user_id}", status_code=302)

from datetime import datetime


@router_user.post("/reserve_meeting")
def reserve_meeting(
        request: Request,
        reservation_date: date = Form(...),
        user_id: int = Form(...),
        start_time: str = Form(...),
        end_time: str = Form(...),
        participants: int = Form(...),
        subject: str = Form(...),
        db: Session = Depends(get_db)
):
    start_time_obj = datetime.strptime(start_time, "%H:%M").time()
    end_time_obj = datetime.strptime(end_time, "%H:%M").time()

    # بررسی تداخل زمانی
    overlapping = db.query(MeetingRoomReservation).filter(
        MeetingRoomReservation.reservation_date == reservation_date,
        MeetingRoomReservation.start_time < end_time_obj,
        MeetingRoomReservation.end_time > start_time_obj
    ).first()
    if reservation_date < date.today():
        request.session["error_message"] = "تاریخ نا معتبر"
        return RedirectResponse(url=f"/user_dashboard?user_id={user_id}", status_code=302)

    if overlapping:
        request.session["error_message"] = "این بازه زمانی قبلاً رزرو شده است."
        return RedirectResponse(url=f"/user_dashboard?user_id={user_id}", status_code=302)

    reservation = MeetingRoomReservation(
        user_id=user_id,
        reservation_date=reservation_date,
        start_time=start_time,
        end_time=end_time,
        participants=participants,
        subject=subject
    )
    db.add(reservation)
    db.commit()

    request.session["message"] = "  با موفقیت ثبت شد."
    return RedirectResponse(url=f"/user_dashboard?user_id={user_id}", status_code=302)

@router_user.post("/delete_meeting")
def delete_meeting(request: Request, meeting_id: int = Form(...), user_id: int = Form(...), db: Session = Depends(get_db)):
    meeting = db.query(MeetingRoomReservation).filter(MeetingRoomReservation.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="جلسه پیدا نشد.")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="شما اجازه حذف این جلسه را ندارید.")

    db.delete(meeting)
    db.commit()

    return RedirectResponse(url=f"/user_dashboard?user_id={user_id}", status_code=303)


# @router_user.get("/order_rep")
# def order_report(user_id: int = Form(...), db: Session = Depends(get_db)):
#     orders= db.query(LunchOrder).filter(LunchOrder.user_id==user_id).all()
#     if orders.order_date== date.today() + timedelta(days=1):
#