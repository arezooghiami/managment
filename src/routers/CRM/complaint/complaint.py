from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, List
from h11 import Response
import jdatetime
import pandas as pd
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy import or_, distinct
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased
from sqlalchemy.orm import joinedload
from fastapi.responses import StreamingResponse

from DB.database import get_db
from models.ComplaintIssue import ComplaintIssue
from models.branch import Branch, Unit
from models.complaint import CustomerComplaint
from models.manager import RegionalManager
from models.user import User

router_complaint = APIRouter(
    tags=["Customer_complaint"],  # ← تگ دسته‌بندی در سوَگر
)
templates = Jinja2Templates(directory="templates")
from datetime import date


@router_complaint.get("/Customer_complaint_list")
def Customer_complaint_list(
        request: Request,
        db: Session = Depends(get_db),
        start_date: str | None = None,
        end_date: str | None = None,
        user_filter: str | None = None,
        branch_filter: str | None = None
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter(User.id == user_id).first()

    today = date.today()
    shamsi_today = jdatetime.date.fromgregorian(date=today).strftime('%Y/%m/%d')

    issues = db.query(ComplaintIssue).all()
    branches = db.query(Branch).all()
    units = db.query(Unit).all()

    def to_jalali(dt):
        if dt:
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
        return ""

    # ==================================================
    # ✅ ادمین → همه شکایات (با یا بدون فیلتر)
    # ==================================================
    if role == "admin":
        query = db.query(CustomerComplaint)

        # فیلتر تاریخ
        # 📅 از تاریخ
        if start_date:
            start_g = jdatetime.datetime.strptime(
                start_date, "%Y/%m/%d"
            ).togregorian()
            query = query.filter(CustomerComplaint.created_at >= start_g)

        # 📅 تا تاریخ
        if end_date:
            end_g = jdatetime.datetime.strptime(
                end_date, "%Y/%m/%d"
            ).togregorian()
            end_g = end_g.replace(hour=23, minute=59, second=59)
            query = query.filter(CustomerComplaint.created_at <= end_g)

        # 🏢 شعبه
        if branch_filter and branch_filter.isdigit():
            query = query.filter(
                CustomerComplaint.branch_id == int(branch_filter)
            )

        # 👤 فیلتر ثبت‌کننده
        if user_filter and user_filter.isdigit():
            query = query.filter(
                CustomerComplaint.user_id == int(user_filter)
            )

        complaints = (
            query
            .order_by(CustomerComplaint.created_at.desc())
            .all()
        )

        # if start_date and end_date:
        #     start_g = jdatetime.datetime.strptime(start_date, "%Y/%m/%d").togregorian()
        #     end_g = jdatetime.datetime.strptime(end_date, "%Y/%m/%d").togregorian()
        #     query = query.filter(
        #         CustomerComplaint.created_at >= start_g,
        #         CustomerComplaint.created_at <= end_g
        #     )

        complaints = query.order_by(CustomerComplaint.created_at.desc()).all()

        admin_mode = True

    # ==================================================
    # ✅ کاربر CRM عادی → فقط شکایات امروز خودش
    # ==================================================
    else:
        start_g = datetime.combine(today, datetime.min.time())
        end_g = datetime.combine(today, datetime.max.time())

        complaints = (
            db.query(CustomerComplaint)
            .filter(CustomerComplaint.user_id == user_id)
            .filter(CustomerComplaint.created_at >= start_g)
            .filter(CustomerComplaint.created_at <= end_g)
            .order_by(CustomerComplaint.created_at.desc())
            .all()
        )

        admin_mode = False

    # ==================================================
    # تبدیل خروجی برای template
    # ==================================================
    complaint_users = (
        db.query(User)
        .join(CustomerComplaint, CustomerComplaint.user_id == User.id)
        .distinct()
        .order_by(User.name)
        .all()
    )
    complaints_final = []
    for c in complaints:
        complaints_final.append({
            "id": c.id,
            "customer_name": c.customer_name,
            "customer_phone": c.customer_phone,
            "created_at_shamsi": to_jalali(c.created_at),
            "branch_name": c.branch.name if c.branch else "—",
            "unit_name": c.unit.name if c.unit else "—",
            "user_name": c.user.name if c.user else "",
            "user_family": c.user.family if c.user else "",
            "description": c.description,
            "tracking_code": c.tracking_code,
            "branch_filter": branch_filter,
            "user_filter": user_filter
        })

    return templates.TemplateResponse(
        "crm/Customer_complaint_list.html",
        {
            "request": request,
            "user": user,
            "today": shamsi_today,
            "complaints": complaints_final,
            "admin_mode": admin_mode,
            "start_date": start_date,
            "end_date": end_date,
            "issues": issues,
            "branches": branches,
            "units": units,
            "complaint_users": complaint_users
        }
    )


@router_complaint.post("/complaints/create")
def create_complaint(
        request: Request,
        customer_name: str = Form(...),
        customer_phone: str = Form(...),
        branch_id: Optional[str] = Form(None),
        unit_id: Optional[str] = Form(None),
        issues: List[int] = Form(...),
        description: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    # دریافت کاربر فعلی
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    # بررسی اینکه حداقل یک issue انتخاب شده باشد
    if not issues:
        raise HTTPException(status_code=400, detail="حداقل یک مورد شکایت باید انتخاب شود")

    # دریافت مدیر منطقه اگر شعبه انتخاب شده باشد
    branch_id = int(branch_id) if branch_id else None

    regional_manager_id = None
    if branch_id:
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if branch and branch.regional_manager:
            regional_manager_id = branch.regional_manager.id

    # تولید کد رهگیری
    import uuid
    tracking_code = str(uuid.uuid4())[:8].upper()
    unit_id = int(unit_id) if unit_id else None
    branch_id = int(branch_id) if branch_id else None

    # ایجاد شکایت جدید
    new_complaint = CustomerComplaint(
        user_id=user_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        branch_id=branch_id,
        unit_id=unit_id,
        regional_manager_id=regional_manager_id,
        issues=issues,
        description=description,
        tracking_code=tracking_code,
        created_at=datetime.now()
    )

    db.add(new_complaint)
    db.commit()

    # بازگشت به صفحه لیست
    return RedirectResponse(url="/Customer_complaint_list", status_code=303)


@router_complaint.get("/complaints/{complaint_id}")
def complaint_detail(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(CustomerComplaint).filter(CustomerComplaint.id == complaint_id).first()
    issue_titles = []
    if c.issues:
        issue_titles = [i.name for i in db.query(ComplaintIssue).filter(ComplaintIssue.id.in_(c.issues)).all()]

    def to_jalali(dt):
        if dt:
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d ساعت %H:%M")
        return ""

    return {
        "customer_name": c.customer_name,
        "customer_phone": c.customer_phone,
        "branch_name": c.branch.name if c.branch else None,
        "unit_name": c.unit.name if c.unit else None,
        "description": c.description,
        "issues": issue_titles,
        "user_name": c.user.name,
        "user_family": c.user.family,
        "created_at_shamsi": to_jalali(c.created_at),
        "region_managment": c.regional_manager.name
    }


# @router_complaint.post("/complaints/create")
# def create_complaint(
#         request: Request,
#         customer_name: str,
#         customer_phone: str,
#         branch_id: int = None,
#         unit_id: int = None,
#         issues: list[int] = [],
#         description: str = None,
#
#         db: Session = Depends(get_db)
# ):
#     # دریافت مدیر منطقه اگر شعبه انتخاب شده
#     user_id = request.session.get("user_id")
#     regional_manager_id = None
#     if branch_id:
#         branch = db.query(Branch).filter(Branch.id == branch_id).first()
#         if not branch:
#             raise HTTPException(status_code=404, detail="شعبه یافت نشد")
#         regional_manager_id = branch.regional_manager_id
#
#     # ساخت کد رهگیری یونیک ساده
#     tracking_code = f"CMP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
#
#     complaint = CustomerComplaint(
#         user_id=user_id,
#         customer_name=customer_name,
#         customer_phone=customer_phone,
#         branch_id=branch_id,
#         unit_id=unit_id,
#         regional_manager_id=regional_manager_id,
#         issues=issues,
#         description=description,
#         tracking_code=tracking_code
#     )
#
#     db.add(complaint)
#     db.commit()
#     db.refresh(complaint)
#
#     return {"success": True, "tracking_code": tracking_code}


# فرضیات:
# - CustomerComplaint مدلی که نشان دادی وجود دارد
# - Issue مدلی با id و title وجود دارد
# - Branch، Unit و User مدل‌ها موجودند
# - get_db و تبدیل تاریخ ژالالی به گرگوری (مثل کدی که قبلاً داشتی) موجودند

def ensure_admin_crm(request: Request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    is_crm = request.session.get("is_crm")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not (role == "admin" and is_crm):
        raise HTTPException(status_code=403, detail="Access denied")
    return user_id


@router_complaint.get("/report_page", response_class=HTMLResponse)
async def get_complaint_report_page(
        request: Request,
        db: Session = Depends(get_db),
        templates: Jinja2Templates = Depends(lambda: Jinja2Templates(directory="templates"))
):
    # ✅ فقط ادمین CRM
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    is_crm = request.session.get("is_crm")

    if not user_id:
        return RedirectResponse(url="/", status_code=302)
    if not (role == "admin" and is_crm):
        return RedirectResponse(url="/", status_code=302)
    thirty_days_ago = datetime.now() - timedelta(days=30)

    complaints_query = db.query(CustomerComplaint).filter(
        CustomerComplaint.created_at >= thirty_days_ago
    )

    # ✅ فیلترها
    branches = db.query(Branch).order_by(Branch.name).all()
    units = db.query(Unit).order_by(Unit.name).all()

    # ✅ عناوین شکایت
    issues = (
        db.query(ComplaintIssue)
        .order_by(ComplaintIssue.name)
        .all()
    )

    # ✅ کاربران CRM (ثبت‌کننده شکایت)
    complaint_users = (
        db.query(User)
        .order_by(User.name, User.family)
        .all()
    )

    # ✅ مدیران منطقه (مدل مستقل – درست)
    regional_managers = (
        db.query(RegionalManager)
        .order_by(RegionalManager.name)
        .all()
    )

    # ✅ تاریخ امروز (شمسی)
    today = datetime.utcnow().date()
    shamsi_today = jdatetime.date.fromgregorian(date=today).strftime('%Y/%m/%d')

    # ✅ صفحه اولیه بدون داده
    complaints_final = []
    # ✅ این قسمت اضافه شد (خیلی مهم)
    selected = {
        "branch_id": None,
        "unit_id": None,
        "issue_id": None,
        "regional_manager_id": None,
        "user_id": None,
    }
    complaints_list = complaints_query.all()  # ⚠️ مهم: اجرای query
    for c in complaints_list:
        if c.created_at:
            c.created_at_jalali = jdatetime.datetime.fromgregorian(
                datetime=c.created_at
            ).strftime("%Y/%m/%d %H:%M")
        c.regional_manager_name = (
            c.branch.regional_manager.name
            if c.branch and c.branch.regional_manager
            else ""
        )

    # جمع‌آوری همه آی‌دی‌ها
    all_issue_ids = set()
    for c in complaints_list:
        if c.issues:
            all_issue_ids.update(c.issues)

    issues_dict = {i.id: i.name for i in db.query(ComplaintIssue).filter(ComplaintIssue.id.in_(all_issue_ids)).all()}

    # تبدیل آی‌دی‌ها به نام‌ها
    for c in complaints_list:
        if c.issues:
            c.issues_names = [issues_dict.get(i, str(i)) for i in c.issues]
        else:
            c.issues_names = []

    return templates.TemplateResponse(
        "crm/complaint_report.html",
        {
            "request": request,
            "role": role,
            "is_crm": is_crm,
            "complaints_query": complaints_list,

            "user": db.query(User).filter(User.id == user_id).first(),
            "today": shamsi_today,

            "complaints": complaints_final,
            "admin_mode": True,

            "start_date": None,
            "end_date": None,

            "issues": issues,
            "branches": branches,
            "units": units,
            "complaint_users": complaint_users,
            "regional_managers": regional_managers,
            "selected": selected,
        }
    )

@router_complaint.post("/complaints/report", response_class=HTMLResponse)
def complaint_report(
        request: Request,
        jalali_date_start: str = Form(...),
        jalali_date_end: str = Form(...),
        branch_id: Optional[str] = Form(None),
        unit_id: Optional[str] = Form(None),
        issue_id: Optional[str] = Form(None),
        regional_manager_id: Optional[str] = Form(None),
        customer_query: Optional[str] = Form(None),
        db: Session = Depends(get_db),
        templates: Jinja2Templates = Depends(lambda: Jinja2Templates(directory="templates"))
):
    # --------------------------------------------------
    # 🔐 Authentication
    # --------------------------------------------------
    if not request.session.get("user_id"):
        return RedirectResponse("/", status_code=302)

    if not (request.session.get("role") == "admin" and request.session.get("is_crm")):
        raise HTTPException(status_code=403, detail="Access denied")

    # --------------------------------------------------
    # 📅 Date conversion (Jalali → Gregorian)
    # --------------------------------------------------
    try:
        start_date = jdatetime.datetime.strptime(
            jalali_date_start, "%Y/%m/%d"
        ).togregorian()

        end_date = (
                jdatetime.datetime.strptime(jalali_date_end, "%Y/%m/%d")
                + timedelta(days=1)
        ).togregorian()
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": "فرمت تاریخ نامعتبر است"}
        )

    # --------------------------------------------------
    # 🧩 Normalize filters
    # --------------------------------------------------
    branch_id = int(branch_id) if branch_id else None
    unit_id = int(unit_id) if unit_id else None
    issue_id = int(issue_id) if issue_id else None
    regional_manager_id = int(regional_manager_id) if regional_manager_id else None

    # --------------------------------------------------
    # 🔍 Base query (Reusable)
    # --------------------------------------------------
    base_query = db.query(CustomerComplaint).filter(
        CustomerComplaint.created_at >= start_date,
        CustomerComplaint.created_at < end_date
    )

    if branch_id:
        base_query = base_query.filter(CustomerComplaint.branch_id == branch_id)

    if unit_id:
        base_query = base_query.filter(CustomerComplaint.unit_id == unit_id)

    if regional_manager_id:
        base_query = base_query.filter(
            CustomerComplaint.regional_manager_id == regional_manager_id
        )

    if issue_id:
        base_query = base_query.filter(CustomerComplaint.issues.any(issue_id))

    if customer_query:
        base_query = base_query.filter(
            or_(
                CustomerComplaint.customer_name.ilike(f"%{customer_query}%"),
                CustomerComplaint.customer_phone.ilike(f"%{customer_query}%")
            )
        )

    # --------------------------------------------------
    # 📄 Complaints list
    # --------------------------------------------------
    complaints = (
        base_query
        .options(
            joinedload(CustomerComplaint.branch),
            joinedload(CustomerComplaint.unit),
            joinedload(CustomerComplaint.user)
        )
        .order_by(CustomerComplaint.created_at.desc())
        .all()
    )

    total_count = len(complaints)

    # --------------------------------------------------
    # 🏷 Issue names mapping
    # --------------------------------------------------
    issue_ids = {i for c in complaints for i in (c.issues or [])}
    issue_map = {
        i.id: i.name
        for i in db.query(ComplaintIssue).filter(ComplaintIssue.id.in_(issue_ids)).all()
    } if issue_ids else {}

    for c in complaints:
        c.created_at_jalali = (
            jdatetime.datetime.fromgregorian(datetime=c.created_at)
            .strftime("%Y/%m/%d %H:%M")
            if c.created_at else "-"
        )
        c.issues_names = [issue_map.get(i, "نامشخص") for i in (c.issues or [])]

    # --------------------------------------------------
    # 📊 Global stats
    # --------------------------------------------------
    stats = db.query(
        func.count(CustomerComplaint.id),
        func.count(distinct(CustomerComplaint.customer_phone)),
        func.count(distinct(CustomerComplaint.branch_id))
    ).filter(
        CustomerComplaint.created_at >= start_date,
        CustomerComplaint.created_at < end_date
    ).first()

    # --------------------------------------------------
    # 📊 Average complaints per customer
    # --------------------------------------------------
    avg_complaints = (
        round(stats[0] / stats[1], 2)
        if stats and stats[1] else 0
    )

    # --------------------------------------------------
    # 📌 Issue specific stats
    # --------------------------------------------------
    issue_stats = []

    if issue_id:
        issue_count = base_query.count()

        total_in_period = db.query(func.count(CustomerComplaint.id)).filter(
            CustomerComplaint.created_at >= start_date,
            CustomerComplaint.created_at < end_date
        ).scalar() or 0

        percent = round((issue_count / total_in_period) * 100, 2) if total_in_period else 0

        issue_stats.append({
            "id": issue_id,
            "title": db.query(ComplaintIssue.name).filter(ComplaintIssue.id == issue_id).scalar(),
            "count": issue_count,
            "percent": percent
        })

    # --------------------------------------------------
    # 📈 Branch stats
    # --------------------------------------------------
    branch_stats = []
    if not branch_id:
        branch_stats = db.query(
            Branch.name,
            func.count(CustomerComplaint.id),
            func.count(distinct(CustomerComplaint.customer_phone))
        ).join(CustomerComplaint).filter(
            CustomerComplaint.created_at >= start_date,
            CustomerComplaint.created_at < end_date
        ).group_by(Branch.name).all()

    # --------------------------------------------------
    # 🧠 Filter impact
    # --------------------------------------------------
    filter_impact = {}
    if branch_id:
        branch_name = db.query(Branch.name).filter(Branch.id == branch_id).scalar()
        filter_impact["branch_name"] = branch_name

    if issue_id:
        filter_impact["issue_name"] = db.query(
            ComplaintIssue.name
        ).filter(ComplaintIssue.id == issue_id).scalar()

    # --------------------------------------------------
    # 📦 Dropdown data
    # --------------------------------------------------
    context = {
        "request": request,
        "start_date": jalali_date_start,
        "end_date": jalali_date_end,
        "complaints_query": complaints,
        "total_count": total_count,
        "unique_customers": stats[1] if stats else 0,
        "unique_branches": stats[2] if stats else 0,
        "avg_complaints_per_customer": avg_complaints,
        "issue_stats": issue_stats,
        "branch_stats": branch_stats,
        "filter_impact": filter_impact,
        "branches": db.query(Branch).all(),
        "units": db.query(Unit).all(),
        "regional_managers": db.query(RegionalManager).all(),
        "issues": db.query(ComplaintIssue).all(),
        "selected": {
            "branch_id": branch_id,
            "unit_id": unit_id,
            "issue_id": issue_id,
            "regional_manager_id": regional_manager_id,
            "customer_query": customer_query
        }
    }

    return templates.TemplateResponse("crm/complaint_report.html", context)

@router_complaint.post("/complaints/report/export")
def export_complaint_report(
        request: Request,
        jalali_date_start: str = Form(...),
        jalali_date_end: str = Form(...),
        branch_id: str = Form(None),
        unit_id: str = Form(None),
        issue_id: str = Form(None),
        regional_manager_id: str = Form(None),
        customer_query: Optional[str] = Form(None),
        export_type: str = Form("detailed"),
        db: Session = Depends(get_db)
):
    import urllib.parse  # ⬅ اضافه مهم

    # احراز هویت
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    is_crm = request.session.get("is_crm")

    if not user_id:
            return RedirectResponse(url="/", status_code=302)
    if not (role == "admin" and is_crm):
        raise HTTPException(status_code=403, detail="Access denied")

    # تبدیل تاریخ شمسی
    try:
        start_date_jalali = jdatetime.datetime.strptime(jalali_date_start, "%Y/%m/%d")
        end_date_jalali = jdatetime.datetime.strptime(jalali_date_end, "%Y/%m/%d")
        end_date_jalali += timedelta(days=1)
        start_date = start_date_jalali.togregorian()
        end_date = end_date_jalali.togregorian()
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "فرمت تاریخ نامعتبر است",
                "message": "لطفا تاریخ‌ها را به فرمت صحیح (مثلاً 1403/01/01) وارد کنید."
            }
        )

    # پایه کوئری
    query = db.query(CustomerComplaint).options(
        joinedload(CustomerComplaint.branch),
        joinedload(CustomerComplaint.unit),
        joinedload(CustomerComplaint.regional_manager),
        joinedload(CustomerComplaint.user)
    ).filter(
        CustomerComplaint.created_at >= start_date,
        CustomerComplaint.created_at < end_date
    )

    # فیلترها
    if branch_id:
        query = query.filter(CustomerComplaint.branch_id == int(branch_id))
    if unit_id:
        query = query.filter(CustomerComplaint.unit_id == int(unit_id))
    if regional_manager_id:
        query = query.filter(CustomerComplaint.regional_manager_id == int(regional_manager_id))
    if issue_id:
        query = query.filter(CustomerComplaint.issues.any(int(issue_id)))
    if customer_query:
        query = query.filter(
            or_(
                CustomerComplaint.customer_name.ilike(f"%{customer_query}%"),
                CustomerComplaint.customer_phone.ilike(f"%{customer_query}%")
            )
        )

    complaints = query.order_by(CustomerComplaint.created_at.desc()).all()

    # داده اکسل
    excel_data = []

    if export_type == "detailed":
        for c in complaints:
            created_at_jalali = ""
            if c.created_at:
                created_at_jalali = jdatetime.datetime.fromgregorian(
                    datetime=c.created_at
                ).strftime("%Y/%m/%d %H:%M")

            issue_names = []
            if c.issues:
                r = db.query(ComplaintIssue.name).filter(
                    ComplaintIssue.id.in_(c.issues)
                ).all()
                issue_names = [i[0] for i in r]

            excel_data.append({
                "کد رهگیری": c.tracking_code or "",
                "تاریخ ثبت": created_at_jalali,
                "نام مشتری": c.customer_name or "",
                "شماره تماس": c.customer_phone or "",
                "شعبه": c.branch.name if c.branch else "",
                "واحد": c.unit.name if c.unit else "",
                "مدیر منطقه": c.branch.regional_manager.name
                if c.branch and c.branch.regional_manager
                else "",
                "موضوع شکایت": "، ".join(issue_names),
                "شرح شکایت": c.description or "",
                "کاربر ثبت کننده": f"{c.user.name} {c.user.family}" if c.user else "",
            })

        filename_fa = f"شکایات_مشتریان_{jalali_date_start}_تا_{jalali_date_end}.xlsx"
        sheet_name = "شکایات"

    elif export_type == "summary":
        for c in complaints:
            created_at_jalali = ""
            if c.created_at:
                created_at_jalali = jdatetime.datetime.fromgregorian(
                    datetime=c.created_at
                ).strftime("%Y/%m/%d")

            excel_data.append({
                "کد رهگیری": c.tracking_code or "",
                "تاریخ": created_at_jalali,
                "نام مشتری": c.customer_name or "",
                "شماره تماس": c.customer_phone or "",
                "شعبه": c.branch.name if c.branch else "",
                "موضوع": c.complaint_title or "",
                "وضعیت": c.status or "",
            })

        filename_fa = f"خلاصه_شکایات_{jalali_date_start}_تا_{jalali_date_end}.xlsx"
        sheet_name = "خلاصه"

    else:
        raise HTTPException(status_code=400, detail="نوع خروجی نامعتبر است")

    # ساخت اکسل
    df = pd.DataFrame(excel_data)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_len = max(len(str(c.value)) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    output.seek(0)

    # ساخت هدرها
    safe_filename = f"complaints_{jalali_date_start}_to_{jalali_date_end}.xlsx"
    encoded_filename = urllib.parse.quote(filename_fa)

    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{safe_filename}\"; "
            f"filename*=UTF-8''{encoded_filename}"
        )
    }

    # استفاده صحیح از Response
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )