import re

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.templating import Jinja2Templates
from persiantools.jdatetime import JalaliDate
from DB.database import get_db
from models.meet import MeetingRoomReservation, MeetingRoom
from models.notification import Notification
from models.roomLock import RoomLock

router_admin = APIRouter(tags=["meeting_room"])
templates = Jinja2Templates(directory="templates")
import jdatetime
from datetime import datetime, date, timedelta, time


@router_admin.get("/admin/locked_rooms", response_class=HTMLResponse)
def view_locked_rooms(request: Request, db: Session = Depends(get_db)):
    role = request.session.get("role")
    office_id = request.session.get("office_id")

    if role != 'admin' or not office_id:
        return RedirectResponse(url="/", status_code=302)

    today = date.today()
    rooms = db.query(MeetingRoom).filter(MeetingRoom.office_id == office_id).all()

    # گرفتن رزروهای از امروز به بعد، فقط برای دفتر خودش
    upcoming_reservations = (
        db.query(MeetingRoomReservation)
        .join(MeetingRoom, MeetingRoomReservation.meeting_room_id == MeetingRoom.id)
        .filter(MeetingRoom.office_id == office_id)
        .filter(MeetingRoomReservation.reservation_date >= today)
        .order_by(MeetingRoomReservation.reservation_date.asc(), MeetingRoomReservation.start_time.asc())
        .all()
    )
    locked_room = (db.query(RoomLock).filter(RoomLock.office_id == office_id)).all()
    for room in locked_room:
        room.start_date_jalali = JalaliDate.to_jalali(room.start_date).strftime("%Y/%m/%d")
        room.end_date_jalali = JalaliDate.to_jalali(room.end_date).strftime("%Y/%m/%d")

    message = request.session.pop("message", None)  # حذف پیام موفقیت
    error = request.session.pop("error", None)

    return templates.TemplateResponse("admin/locked_rooms.html", {
        "request": request,
        "reservations": upcoming_reservations,
        "locked_room": locked_room,
        "rooms": rooms,
        "message": message,
        "error": error
    })


@router_admin.post("/lock_room")
def lock_room(
        request: Request,
        room_id: int = Form(...),
        start_date: str = Form(...),
        end_date: str = Form(...),
        start_time: str = Form(None),
        end_time: str = Form(None),
        reason: str = Form(...),
        db: Session = Depends(get_db),
):
    admin_office_id = request.session.get("office_id")
    role = request.session.get("role")
    if not admin_office_id or role != 'admin':
        return RedirectResponse(url="/", status_code=302)

    # بررسی مالکیت اتاق
    room = db.query(MeetingRoom).filter(MeetingRoom.id == room_id).first()
    if not room or room.office_id != admin_office_id:
        raise HTTPException(status_code=403, detail="شما مجاز به قفل کردن این اتاق نیستید.")

    # تبدیل تاریخ شمسی به میلادی
    date_pattern = r"^\d{4}/\d{2}/\d{2}$"
    if not re.match(date_pattern, start_date) or not re.match(date_pattern, end_date):
        raise HTTPException(status_code=400, detail="فرمت تاریخ باید به صورت YYYY/MM/DD باشد.")

    try:
        start_j = jdatetime.date(*map(int, start_date.split('/')))
        end_j = jdatetime.date(*map(int, end_date.split('/')))
        start_g = start_j.togregorian()
        end_g = end_j.togregorian()
    except ValueError:
        raise HTTPException(status_code=400, detail="مقدار تاریخ نامعتبر است.")
    if start_g > end_g:
        raise HTTPException(status_code=400, detail="تاریخ شروع باید قبل از تاریخ پایان باشد.")

    # تبدیل ساعت‌ها
    try:
        start_time_obj = datetime.strptime(start_time, "%H:%M").time() if start_time else time(0, 0)
        end_time_obj = datetime.strptime(end_time, "%H:%M").time() if end_time else time(23, 59)
    except:
        raise HTTPException(status_code=400, detail="فرمت ساعت نادرست است.")

    if start_time_obj >= end_time_obj:
        raise HTTPException(status_code=400, detail="ساعت شروع باید قبل از پایان باشد.")
    current_date = start_g
    overlapping_dates = []
    while current_date <= end_g:
        existing_lock = db.query(RoomLock).filter(
            RoomLock.meeting_room_id == room_id,
            RoomLock.start_date <= current_date,
            RoomLock.end_date >= current_date,
            RoomLock.start_time < end_time_obj,
            RoomLock.end_time > start_time_obj
        ).first()
        if existing_lock:
            overlapping_dates.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)

    if overlapping_dates:
        request.session["message"] = f"امکان قفل کردن وجود ندارد.  قبلاً قفل ثبت شده است: "
        return RedirectResponse(url="/admin/locked_rooms", status_code=303)

    # پیمایش بین start_g و end_g برای قفل کردن هر روز
    current_date = start_g
    while current_date <= end_g:
        # بررسی وجود قفل قبلی
        existing_lock = db.query(RoomLock).filter(
            RoomLock.meeting_room_id == room_id,
            RoomLock.start_date <= current_date,
            RoomLock.end_date >= current_date,
            RoomLock.start_time < end_time_obj,
            RoomLock.end_time > start_time_obj
        ).first()
        if existing_lock:
            current_date += timedelta(days=1)
            continue  # پرش به روز بعد

        # حذف رزروهای متداخل
        conflicting_reservations = db.query(MeetingRoomReservation).filter(
            MeetingRoomReservation.meeting_room_id == room_id,
            MeetingRoomReservation.reservation_date == current_date,
            MeetingRoomReservation.start_time < end_time_obj,
            MeetingRoomReservation.end_time > start_time_obj
        ).all()

        for res in conflicting_reservations:
            notification = Notification(
                user_id=res.user_id,
                message=f"رزرو شما برای اتاق {room.name} در تاریخ {current_date.strftime('%Y-%m-%d')} بین {start_time_obj.strftime('%H:%M')} تا {end_time_obj.strftime('%H:%M')} به دلیل «{reason}» لغو شد.",
                created_at=datetime.utcnow()
            )
            db.add(notification)
            db.delete(res)

        # ثبت قفل جدید
        lock = RoomLock(
            meeting_room_id=room_id,
            office_id=admin_office_id,
            start_date=current_date,
            end_date=current_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            reason=reason
        )
        db.add(lock)

        current_date += timedelta(days=1)

    db.commit()
    request.session["message"] = "اتاق با موفقیت قفل شد و رزروهای متداخل حذف شدند."
    return RedirectResponse(url="/admin/locked_rooms", status_code=303)


@router_admin.post("/unlock_room/{lock_id}")
def unlock_room(lock_id: int, request: Request, db: Session = Depends(get_db)):
    lock = db.query(RoomLock).filter(RoomLock.id == lock_id).first()
    if not lock:
        raise HTTPException(status_code=404, detail="قفل مورد نظر یافت نشد.")

    db.delete(lock)
    db.commit()

    request.session["message"] = "قفل با موفقیت حذف شد."
    return RedirectResponse(url="/admin/locked_rooms", status_code=303)
