from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from DB.database import get_db
from models.meet import MeetingRoomReservation
from models.user import User

from starlette.templating import Jinja2Templates

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")
from datetime import datetime, time


@router_user.get("/user_meetingroom")
def user_meetingroom(request: Request, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    tomorrow = date.today() + timedelta(days=1)

    meetings = db.query(MeetingRoomReservation).options(joinedload(MeetingRoomReservation.user)).all()

    return templates.TemplateResponse("user/user_meetingroom.html", {
        "request": request,
        "user": user,

        "meetings": meetings,
        "today": date.today()
    })


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
    return RedirectResponse(url=f"/user_meetingroom?user_id={user_id}", status_code=302)


@router_user.post("/delete_meeting")
def delete_meeting(request: Request, meeting_id: int = Form(...), user_id: int = Form(...),
                   db: Session = Depends(get_db)):
    meeting = db.query(MeetingRoomReservation).filter(MeetingRoomReservation.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="جلسه پیدا نشد.")

    if meeting.user_id != user_id:
        raise HTTPException(status_code=403, detail="شما اجازه حذف این جلسه را ندارید.")

    db.delete(meeting)
    db.commit()

    return RedirectResponse(url=f"/user_meetingroom?user_id={user_id}", status_code=302)
