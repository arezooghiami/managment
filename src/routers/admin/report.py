import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session, joinedload
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.lunch import LunchOrder
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")
import jdatetime
from datetime import datetime


@router.get("/lunch/admin/report")
def lunch_report_get(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()

    lunch_rep = db.query(LunchOrder).options(joinedload(LunchOrder.user)).filter(
        LunchOrder.order_date == datetime.today(),
        LunchOrder.user.has(office_id=user.office_id)
    ).all()

    return templates.TemplateResponse("admin/lunch_report.html", {
        "request": request,
        "lunches": lunch_rep,
        "selected_date": None
    })


@router.post("/lunch/admin/report")
def lunch_report_post(
        request: Request,
        jalali_date: str = Form(...),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    try:
        parts = [int(p) for p in jalali_date.split('/')]
        jalali = jdatetime.date(parts[0], parts[1], parts[2])
        gregorian = jalali.togregorian()
    except Exception:
        return templates.TemplateResponse("admin/lunch_report.html", {
            "request": request,
            "lunches": [],
            "selected_date": None,
            "error": "فرمت تاریخ نادرست است."
        })
    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()

    lunch_rep = db.query(LunchOrder).options(joinedload(LunchOrder.user)).filter(
        LunchOrder.order_date == gregorian,
        LunchOrder.user.has(office_id=user.office_id)
    ).all()

    return templates.TemplateResponse("admin/lunch_report.html", {
        "request": request,
        "lunches": lunch_rep,
        "selected_date": jalali
    })


@router.post("/lunch_count/admin/report")
def lunch_count_report_post(
        request: Request,
        jalali_date_start: str = Form(...),
        jalali_date_end: str = Form(...),
        code: str = Form(...),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    try:
        parts = [int(p) for p in jalali_date_start.split('/')]
        gregorian_start = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()

        parts = [int(p) for p in jalali_date_end.split('/')]
        gregorian_end = jdatetime.date(parts[0], parts[1], parts[2]).togregorian()
    except Exception:
        return templates.TemplateResponse("admin/lunch_report.html", {
            "request": request,
            "lunches": [],
            "selected_date": None,
            "error": "فرمت تاریخ نادرست است."
        })

    user_id = request.session.get("user_id")
    admin_user = db.query(User).filter(User.id == user_id).first()

    if not admin_user:
        return templates.TemplateResponse("admin/lunch_report.html", {
            "request": request,
            "lunches": [],
            "selected_date": None,
            "error": "دسترسی نامعتبر است."
        })

    # پیدا کردن یوزر با کد پرسنلی
    target_user = db.query(User).filter(
        User.code == code,
        User.office_id == admin_user.office_id
    ).first()

    if not target_user:
        return templates.TemplateResponse("admin/lunch_report.html", {
            "request": request,
            "lunches": [],
            "selected_date": None,
            "error": "کاربری با این کد یافت نشد."
        })

    lunch_rep = db.query(LunchOrder).options(joinedload(LunchOrder.user)).filter(
        LunchOrder.order_date >= gregorian_start,
        LunchOrder.order_date <= gregorian_end,
        LunchOrder.user_id == target_user.id
    ).all()

    return templates.TemplateResponse("admin/lunch_report.html", {
        "request": request,
        "lunches": lunch_rep,
        "selected_date": f"{jalali_date_start} تا {jalali_date_end}"
    })


@router.get("/lunch/admin/report/export")
def export_lunch_excel(db: Session = Depends(get_db)):
    tomorrow = date.today() + timedelta(days=1)
    lunch_rep = db.query(LunchOrder).filter(LunchOrder.order_date == tomorrow).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Lunch Report"

    # Header
    ws.append(["کدپرسنلی", "نام کاربر", "نوع غذا", "مهمان"])

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
