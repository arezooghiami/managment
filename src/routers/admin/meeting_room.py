from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, timedelta, time
from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from DB.database import get_db
from models.meet import MeetingRoomReservation, MeetingRoom
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/meetingroom")
def admin_meetingroom(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    today = date.today()
    end_day = today + timedelta(days=7)
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    reservations = db.query(MeetingRoomReservation).options(
        joinedload(MeetingRoomReservation.meeting_room)
    ).filter(
        MeetingRoomReservation.reservation_date >= today,
        MeetingRoomReservation.reservation_date <= end_day,
        MeetingRoomReservation.office_id == user.office_id
    ).order_by(
        MeetingRoomReservation.reservation_date,
        MeetingRoomReservation.start_time
    ).all()

    # گروه‌بندی بر اساس تاریخ
    grouped = {}
    for res in reservations:
        day = res.reservation_date
        if day not in grouped:
            grouped[day] = []
        grouped[day].append(res)

    return templates.TemplateResponse("admin/meetingroom.html", {
        "request": request,
        "grouped_reservations": grouped
    })

@router.post("/admin/meetingroom/delete/{reservation_id}")
def delete_reservation(reservation_id: int, db: Session = Depends(get_db)):
    res = db.query(MeetingRoomReservation).get(reservation_id)
    if res:
        db.delete(res)
        db.commit()
    return RedirectResponse(url="/admin/meetingroom", status_code=303)
