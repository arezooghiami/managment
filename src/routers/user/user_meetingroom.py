from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from DB.database import get_db
from models.meet import MeetingRoomReservation, MeetingRoom
from models.user import User

from starlette.templating import Jinja2Templates

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")
from datetime import datetime, time


@router_user.get("/user_meetingroom")
def user_meetingroom(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)
    user = db.query(User).filter(User.id == user_id).first()
    tomorrow = date.today() + timedelta(days=1)
    user = db.query(User).filter(User.id == user_id).first()
    meeting_rooms = db.query(MeetingRoom).filter(MeetingRoom.office_id == user.office_id).all()

    meetings = db.query(MeetingRoomReservation).options(joinedload(MeetingRoomReservation.user)).all()

    return templates.TemplateResponse("user/user_meetingroom.html", {
        "request": request,
        "user": user,
        "meeting_rooms": meeting_rooms,
        "meetings": meetings,
        "today": date.today()
    })


@router_user.post("/reserve_meeting")
def reserve_meeting(
        request: Request,
        user_id: int = Form(...),
        reservation_date: date = Form(...),
        start_time: str = Form(...),
        end_time: str = Form(...),
        participants: int = Form(...),
        subject: str = Form(...),
        selected_room: int = Form(...),

        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)
    start_time_obj = datetime.strptime(start_time, "%H:%M").time()
    end_time_obj = datetime.strptime(end_time, "%H:%M").time()
    user = db.query(User).filter(User.id == user_id).first()

    # Fetch the selected meeting room
    meeting_room = db.query(MeetingRoom).filter(MeetingRoom.id == selected_room).first()

    if meeting_room.capacity < participants:
        request.session["error_message"] = "ظرفیت اتاق کمتر از تعداد افراد جلسه است."
        return RedirectResponse(url=f"/user_meetingroom?user_id={user_id}", status_code=302)

    # Check for overlapping reservations
    overlapping = db.query(MeetingRoomReservation).filter(
        MeetingRoomReservation.reservation_date == reservation_date,
        MeetingRoomReservation.start_time < end_time_obj,
        MeetingRoomReservation.end_time > start_time_obj,
        MeetingRoomReservation.meeting_room_id == selected_room
    ).first()
    if reservation_date < date.today():
        request.session["error_message"] = "تاریخ نامعتبر"
        return RedirectResponse(url=f"/user_meetingroom?user_id={user_id}", status_code=302)

    if overlapping:
        request.session["error_message"] = "این بازه زمانی قبلاً رزرو شده است."
        return RedirectResponse(url=f"/user_meetingroom", status_code=302)

    reservation = MeetingRoomReservation(
        user_id=user_id,
        reservation_date=reservation_date,
        start_time=start_time,
        end_time=end_time,
        participants=participants,
        subject=subject,
        office_id=user.office_id,
        meeting_room_id=selected_room  # Correct field name
    )
    db.add(reservation)
    db.commit()

    request.session["message"] = "با موفقیت ثبت شد."
    return RedirectResponse(url=f"/user_meetingroom", status_code=302)




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
