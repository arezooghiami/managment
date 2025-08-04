from datetime import date, timedelta

import jdatetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.meet import MeetingRoomReservation, MeetingRoom
from models.roomLock import RoomLock
from models.user import User

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")
from datetime import datetime


def convert_persian_digits_to_english(persian_str: str) -> str:
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(''.join(persian_digits), ''.join(english_digits))
    return persian_str.translate(translation_table)


@router_user.get("/user_meetingroom")
def user_meetingroom(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    tomorrow = date.today() + timedelta(days=1)
    meeting_rooms = db.query(MeetingRoom).filter(MeetingRoom.office_id == user.office_id).all()
    # meetings = db.query(MeetingRoomReservation).options(joinedload(MeetingRoomReservation.user)).all()
    meetings = db.query(MeetingRoomReservation) \
        .options(joinedload(MeetingRoomReservation.user)) \
        .filter(MeetingRoomReservation.reservation_date >= date.today()) \
        .order_by(MeetingRoomReservation.reservation_date, MeetingRoomReservation.start_time) \
        .all()


    # اضافه کردن تاریخ شمسی به هر meeting
    for meeting in meetings:
        meeting.jalali_date = jdatetime.date.fromgregorian(date=meeting.reservation_date).strftime('%Y/%m/%d')

    today_shamsi = jdatetime.date.fromgregorian(date=date.today()).strftime('%Y/%m/%d')
    tomorrow_shamsi = jdatetime.date.fromgregorian(date=tomorrow).strftime('%Y/%m/%d')

    return templates.TemplateResponse("user/user_meetingroom.html", {
        "request": request,
        "user": user,
        "meeting_rooms": meeting_rooms,
        "meetings": meetings,
        "today": today_shamsi,
        "tomorrow": tomorrow_shamsi,
        "form_errors": {},   # 👈 اضافه شود
        "form_data": {}
    })
@router_user.post("/reserve_meeting", response_class=HTMLResponse)
async def reserve_meeting(
        request: Request,
        reservation_date: str = Form(...),
        start_time: str = Form(...),
        end_time: str = Form(...),
        participants: str = Form(...),
        subject: str = Form(...),
        selected_room: int = Form(...),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)

    form_errors = {}
    form_data = {
        "reservation_date": reservation_date,
        "start_time": start_time,
        "end_time": end_time,
        "participants": participants,
        "subject": subject,
        "selected_room": selected_room
    }

    # تبدیل تاریخ
    try:
        clean_date_str = convert_persian_digits_to_english(reservation_date)
        parts = [int(p) for p in clean_date_str.split('/')]
        jalali_date = jdatetime.date(parts[0], parts[1], parts[2])
        gregorian_date = jalali_date.togregorian()
    except:
        form_errors["reservation_date"] = "فرمت تاریخ نادرست است. مثلاً 1404/04/04"

    # تبدیل ساعت
    try:
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()
        if start_time_obj >= end_time_obj:
            form_errors["start_time"] = "ساعت شروع باید قبل از ساعت پایان باشد."
    except:
        form_errors["start_time"] = "فرمت ساعت نادرست است."

    user = db.query(User).filter(User.id == user_id).first()
    meeting_room = db.query(MeetingRoom).filter(MeetingRoom.id == selected_room).first()

    if not user or not meeting_room:
        form_errors["selected_room"] = "کاربر یا اتاق پیدا نشد."
    # بررسی فیلدها
    if participants.strip() == "":
        form_errors["participants"] = "تعداد افراد را وارد کنید"
    else:
        try:
            participants = int(participants)
            if participants <= 0:
                form_errors["participants"] = "تعداد باید عددی مثبت باشد"

            elif  meeting_room and meeting_room.capacity < participants:
                form_errors["participants"] = "ظرفیت اتاق کمتر از تعداد افراد است."
        except ValueError:
            form_errors["participants"] = "تعداد افراد باید عدد باشد"



    if "reservation_date" not in form_errors and gregorian_date < date.today():
        form_errors["reservation_date"] = "تاریخ جلسه نمی‌تواند قبل از امروز باشد."

    if not form_errors:
        # بررسی قفل بودن
        locked = db.query(RoomLock).filter(
            RoomLock.meeting_room_id == selected_room,
            RoomLock.start_date <= gregorian_date,
            RoomLock.end_date >= gregorian_date,
            RoomLock.start_time < end_time_obj,
            RoomLock.end_time > start_time_obj
        ).first()
        if locked:
            form_errors["selected_room"] = (
                f"اتاق در این زمان بسته است: {locked.reason}"
            )

        # بررسی تداخل
        overlapping = db.query(MeetingRoomReservation).filter(
            MeetingRoomReservation.reservation_date == gregorian_date,
            MeetingRoomReservation.start_time < end_time_obj,
            MeetingRoomReservation.end_time > start_time_obj,
            MeetingRoomReservation.meeting_room_id == selected_room
        ).first()
        if overlapping:
            form_errors["selected_room"] = "این بازه قبلاً رزرو شده است."

    if form_errors:
        # نمایش مجدد فرم با خطا و اطلاعات قبلی
        tomorrow = date.today() + timedelta(days=1)
        meetings = db.query(MeetingRoomReservation) \
            .options(joinedload(MeetingRoomReservation.user)) \
            .filter(MeetingRoomReservation.reservation_date >= date.today()) \
            .order_by(MeetingRoomReservation.reservation_date, MeetingRoomReservation.start_time) \
            .all()
        for meeting in meetings:
            meeting.jalali_date = jdatetime.date.fromgregorian(date=meeting.reservation_date).strftime('%Y/%m/%d')

        meeting_rooms = db.query(MeetingRoom).filter(MeetingRoom.office_id == user.office_id).all()

        return templates.TemplateResponse("user/user_meetingroom.html", {
            "request": request,
            "user": user,
            "meeting_rooms": meeting_rooms,
            "meetings": meetings,
            "today": jdatetime.date.fromgregorian(date=date.today()).strftime('%Y/%m/%d'),
            "tomorrow": jdatetime.date.fromgregorian(date=tomorrow).strftime('%Y/%m/%d'),
            "form_data": form_data,
            "form_errors": form_errors
        })

    # ثبت رزرو
    reservation = MeetingRoomReservation(
        user_id=user_id,
        reservation_date=gregorian_date,
        start_time=start_time_obj,
        end_time=end_time_obj,
        participants=participants,
        subject=subject,
        office_id=user.office_id,
        meeting_room_id=selected_room
    )
    db.add(reservation)
    db.commit()

    request.session["message"] = "جلسه با موفقیت رزرو شد."
    return RedirectResponse(url="/user_meetingroom", status_code=302)


# @router_user.post("/reserve_meeting")
# def reserve_meeting(
#         request: Request,
#         reservation_date: str = Form(...),
#         start_time: str = Form(...),
#         end_time: str = Form(...),
#         participants: int = Form(...),
#         subject: str = Form(...),
#         selected_room: int = Form(...),
#         db: Session = Depends(get_db)
# ):
#     # گرفتن اطلاعات از سشن
#     user_id = request.session.get("user_id")
#     role = request.session.get("role")
#     if not user_id or role != 'user':
#         return RedirectResponse(url="/", status_code=302)
#
#     # تبدیل تاریخ شمسی به میلادی
#     try:
#         clean_date_str = convert_persian_digits_to_english(reservation_date)
#         parts = [int(p) for p in clean_date_str.split('/')]
#         jalali_date = jdatetime.date(parts[0], parts[1], parts[2])
#         gregorian_date = jalali_date.togregorian()
#     except Exception as e:
#         request.session["error_message"] = "فرمت تاریخ نادرست است. لطفاً به صورت 1404/04/04 وارد کنید."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#     # تبدیل ساعت‌ها به آبجکت زمان
#     try:
#         start_time_obj = datetime.strptime(start_time, "%H:%M").time()
#         end_time_obj = datetime.strptime(end_time, "%H:%M").time()
#     except:
#         request.session["error_message"] = "فرمت ساعت نادرست است."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#     # بررسی این‌که ساعت شروع باید کمتر از ساعت پایان باشد
#     if start_time_obj >= end_time_obj:
#         request.session["error_message"] = "ساعت شروع باید قبل از ساعت پایان باشد."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#     # بررسی اطلاعات کاربر و اتاق
#     user = db.query(User).filter(User.id == user_id).first()
#     meeting_room = db.query(MeetingRoom).filter(MeetingRoom.id == selected_room).first()
#
#     if not user or not meeting_room:
#         request.session["error_message"] = "کاربر یا اتاق یافت نشد."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#     if meeting_room.capacity < participants:
#         request.session["error_message"] = "ظرفیت اتاق کمتر از تعداد افراد جلسه است."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#     if gregorian_date < date.today():
#         request.session["error_message"] = "تاریخ انتخاب شده معتبر نیست."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#     # بررسی قفل بودن اتاق
#     # بررسی قفل بودن اتاق در تاریخ و بازه ساعتی مورد نظر
#     locked = db.query(RoomLock).filter(
#         RoomLock.meeting_room_id == selected_room,
#         RoomLock.start_date <= gregorian_date,
#         RoomLock.end_date >= gregorian_date,
#         RoomLock.start_time < end_time_obj,
#         RoomLock.end_time > start_time_obj
#     ).first()
#
#     if locked:
#         request.session["error_message"] = (
#             f"رزرو این اتاق برای تاریخ {reservation_date} بین {start_time} تا {end_time} به دلیل «{locked.reason}» مسدود شده است."
#         )
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#
#
#     # بررسی تداخل زمان
#     overlapping = db.query(MeetingRoomReservation).filter(
#         MeetingRoomReservation.reservation_date == gregorian_date,
#         MeetingRoomReservation.start_time < end_time_obj,
#         MeetingRoomReservation.end_time > start_time_obj,
#         MeetingRoomReservation.meeting_room_id == selected_room
#     ).first()
#
#     if overlapping:
#         request.session["error_message"] = "این بازه زمانی قبلاً رزرو شده است."
#         return RedirectResponse(url="/user_meetingroom", status_code=302)
#
#     # ثبت جلسه جدید
#     reservation = MeetingRoomReservation(
#         user_id=user_id,
#         reservation_date=gregorian_date,
#         start_time=start_time_obj,
#         end_time=end_time_obj,
#         participants=participants,
#         subject=subject,
#         office_id=user.office_id,
#         meeting_room_id=selected_room
#     )
#     db.add(reservation)
#     db.commit()
#
#     request.session["message"] = "جلسه با موفقیت رزرو شد."
#     return RedirectResponse(url="/user_meetingroom", status_code=302)


@router_user.post("/delete_meeting")
def delete_meeting(request: Request, meeting_id: int = Form(...), user_id: int = Form(...),
                   db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)
    meeting = db.query(MeetingRoomReservation).filter(MeetingRoomReservation.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="جلسه پیدا نشد.")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="شما اجازه حذف این جلسه را ندارید.")

    db.delete(meeting)
    db.commit()

    return RedirectResponse(url=f"/user_meetingroom", status_code=302)
