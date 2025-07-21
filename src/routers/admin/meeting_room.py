from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta, time
from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse

from DB.database import get_db
from models.meet import MeetingRoomReservation

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin/meetingroom")
def admin_meetingroom(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    end_day = today + timedelta(days=7)

    reservations = db.query(MeetingRoomReservation).filter(
        MeetingRoomReservation.reservation_date >= today,
        MeetingRoomReservation.reservation_date <= end_day
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
