from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, timedelta, time
from starlette.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from fastapi.responses import StreamingResponse
import io
from openpyxl import Workbook

from DB.database import get_db
from models.lunch import LunchOrder
from models.meet import MeetingRoomReservation

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/lunch/admin/report")
def lunch_report(request: Request, db: Session = Depends(get_db)):
    tomorrow = date.today() + timedelta(days=1)
    meetings = db.query(MeetingRoomReservation).options(joinedload(MeetingRoomReservation.user)).all()
    # lunch_rep = db.query(LunchOrder).options(joinedload(LunchOrder.user)).all()
    lunch_rep = db.query(LunchOrder).options(joinedload(LunchOrder.user)).filter(LunchOrder.order_date == tomorrow)
    # lunch_rep = db.query(LunchOrder).options(joinedload(LunchOrder.lunch_menu)).filter(LunchOrder.order_date == tomorrow)
    # lunch_rep = db.query(LunchOrder).filter(LunchOrder.order_date == tomorrow).all()
    return templates.TemplateResponse("admin/lunch_report.html", {
        "request": request,
        "lunches": lunch_rep,
        "tomorrow": tomorrow
    })



@router.get("/lunch/admin/report/export")
def export_lunch_excel(db: Session = Depends(get_db)):
    tomorrow = date.today() + timedelta(days=1)
    lunch_rep = db.query(LunchOrder).filter(LunchOrder.order_date == tomorrow).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Lunch Report"

    # Header
    ws.append(["کدپرسنلی","نام کاربر", "نوع غذا", "مهمان"])

    for item in lunch_rep:
        ws.append([
            item.user.code,
            item.user.name,
            item.selected_dish,
            item.guest_name or ''
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"lunch_report_{tomorrow.strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(stream,
                             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})
