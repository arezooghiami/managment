from io import BytesIO
from openpyxl.styles import Alignment, PatternFill, Font

import jdatetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi import Form
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from openpyxl import Workbook
from persiantools.jdatetime import JalaliDate
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse

from DB.database import get_db
from models.inCall import IncomingCall
from models.outCall import OutCall
from models.user import User

router_crm = APIRouter()
templates = Jinja2Templates(directory="templates")
from datetime import date, datetime


@router_crm.get("/crm_dashboard")
def crm_dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter(User.id == user_id).first()
    today = date.today()
    shamsi_today = jdatetime.date.fromgregorian(date=today).strftime('%Y/%m/%d')

    incoming_call = (
        db.query(IncomingCall)
        .filter(IncomingCall.user_id == user_id, IncomingCall.datetime == today)
        .first()
    )

    out_call = (
        db.query(OutCall)
        .filter(OutCall.user_id == user_id, OutCall.datetime == today)
        .first()
    )

    incoming_data = {
        "posty_code": incoming_call.posty_code if incoming_call and incoming_call.posty_code else 0,
        "send_product_deadline": incoming_call.send_product_deadline if incoming_call and incoming_call.send_product_deadline else 0,
        "branch_change": incoming_call.branch_change if incoming_call and incoming_call.branch_change else 0,
        "online_change": incoming_call.online_change if incoming_call and incoming_call.online_change else 0,
        "online_return": incoming_call.online_return if incoming_call and incoming_call.online_return else 0,
        "branch_dissatisfaction": incoming_call.branch_dissatisfaction if incoming_call and incoming_call.branch_dissatisfaction else 0,
        "payment_followup": incoming_call.payment_followup if incoming_call and incoming_call.payment_followup else 0,
        "incomplete_delivery": incoming_call.incomplete_delivery if incoming_call and incoming_call.incomplete_delivery else 0,
        "b2b_sales": incoming_call.b2b_sales if incoming_call and incoming_call.b2b_sales else 0,
        "waiting_for_payment": incoming_call.waiting_for_payment if incoming_call and incoming_call.waiting_for_payment else 0,
        "product_search": incoming_call.product_search if incoming_call and incoming_call.product_search else 0,
        "after_sales_service": incoming_call.after_sales_service if incoming_call and incoming_call.after_sales_service else 0,
        "club": incoming_call.club if incoming_call and incoming_call.club else 0,
        "other": incoming_call.other if incoming_call and incoming_call.other else 0,
    }

    out_data = {
        "internet": out_call.internet if out_call and out_call.internet else 0,
        "voice_mail": out_call.voice_mail if out_call and out_call.voice_mail else 0
    }
    return templates.TemplateResponse("user/CRM.html", {
        "request": request,
        "user": user,
        "incoming_data": incoming_data,
        "out_data": out_data,
        "today": shamsi_today  # 👈 فقط تاریخ روز
    })


@router_crm.post("/update_crm_data")
async def update_crm_data(
        request: Request,
        db: Session = Depends(get_db)
):
    data = await request.json()
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    # if not user_id or role != 'user':
    #     raise HTTPException(status_code=403, detail="Unauthorized")

    field = data.get("field")
    type_ = data.get("type")  # "incoming" or "out"
    change = data.get("change")  # +1 or -1

    if type_ not in ["incoming", "out"] or not field or change not in [-1, 1]:
        raise HTTPException(status_code=400, detail="Invalid input")

    today = date.today()
    now = datetime.now()

    if type_ == "incoming":
        record = (
            db.query(IncomingCall)
            .filter(IncomingCall.user_id == user_id, IncomingCall.datetime == today)
            .first()
        )
        if not record:
            record = IncomingCall(
                user_id=user_id,
                datetime=today,
                start_datetime=now,
                end_datetime=now
            )
            db.add(record)
            db.commit()
            db.refresh(record)
        else:
            # بروزرسانی زمان پایان تماس
            record.end_datetime = now
            # اگر اولین تماس نیست، زمان شروع رو تغییر نده

        if not hasattr(record, field):
            raise HTTPException(status_code=400, detail="Invalid field name")

        current_value = getattr(record, field) or 0
        new_value = max(0, current_value + change)
        setattr(record, field, new_value)

    elif type_ == "out":
        record = (
            db.query(OutCall)
            .filter(OutCall.user_id == user_id, OutCall.datetime == today)
            .first()
        )
        if not record:
            record = OutCall(
                user_id=user_id,
                datetime=today,

            )
            db.add(record)
            db.commit()
            db.refresh(record)

        if not hasattr(record, field):
            raise HTTPException(status_code=400, detail="Invalid field name")

        current_value = getattr(record, field) or 0
        new_value = max(0, current_value + change)
        setattr(record, field, new_value)

    db.commit()
    return JSONResponse(content={"success": True})


def convert_persian_to_english_numbers(s):
    persian_nums = "۰۱۲۳۴۵۶۷۸۹"
    english_nums = "0123456789"
    for p, e in zip(persian_nums, english_nums):
        s = s.replace(p, e)
    return s


@router_crm.post("/report_crm_data")
async def report_crm_data(
        request: Request,
        jalali_date_start: str = Form(...),
        jalali_date_end: str = Form(...),
        code: str = Form(""),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    is_crm = request.session.get("is_crm")
    code = convert_persian_to_english_numbers(code)
    jalali_date_start = convert_persian_to_english_numbers(jalali_date_start)
    jalali_date_end = convert_persian_to_english_numbers(jalali_date_end)

    try:
        start_date = JalaliDate.strptime(jalali_date_start, "%Y/%m/%d").to_gregorian()
        end_date = JalaliDate.strptime(jalali_date_end, "%Y/%m/%d").to_gregorian()
    except:
        raise HTTPException(status_code=400, detail="فرمت تاریخ اشتباه است.")

    if role == "user" and is_crm:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
        code = user.code

    users_query = db.query(User)
    if code:
        users_query = users_query.filter(User.code == code)
    users = users_query.filter(User.is_crm == True).all()

    results = []

    incoming_fields = [
        "posty_code", "send_product_deadline", "branch_change", "online_change",
        "online_return", "branch_dissatisfaction", "payment_followup", "incomplete_delivery",
        "b2b_sales", "waiting_for_payment", "product_search", "after_sales_service",
        "club", "other"
    ]
    outgoing_fields = ["internet", "voice_mail"]

    # مقدار اولیه مجموع کل همه کاربران
    total_sum_all = {field: 0 for field in incoming_fields + outgoing_fields}
    total_sum_all["total_row_sum"] = 0  # مجموع ردیفی همه کاربران

    for user in users:
        incoming_records = db.query(IncomingCall).filter(
            IncomingCall.user_id == user.id,
            IncomingCall.datetime >= start_date,
            IncomingCall.datetime <= end_date
        ).all()

        out_records = db.query(OutCall).filter(
            OutCall.user_id == user.id,
            OutCall.datetime >= start_date,
            OutCall.datetime <= end_date
        ).all()

        def sum_fields(records, fields):
            return {field: sum(getattr(r, field) or 0 for r in records) for field in fields}

        incoming_data = sum_fields(incoming_records, incoming_fields)
        out_data = sum_fields(out_records, outgoing_fields)

        # محاسبه مجموع ردیفی برای هر کاربر
        total_row_sum = sum(incoming_data.values()) + sum(out_data.values())

        # به‌روزرسانی مجموع کل همه کاربران
        for field, value in {**incoming_data, **out_data}.items():
            total_sum_all[field] += value
        total_sum_all["total_row_sum"] += total_row_sum

        results.append({
            "name": f"{user.name} {user.family}",
            "code": user.code,
            "incoming": incoming_data,
            "out": out_data,
            "total_row_sum": total_row_sum  # ستون مجموع این ردیف
        })

    # افزودن ردیف مجموع کل به انتهای خروجی
    results.append({
        "name": "مجموع کل",
        "code": "-",
        "incoming": {field: total_sum_all[field] for field in incoming_fields},
        "out": {field: total_sum_all[field] for field in outgoing_fields},
        "total_row_sum": total_sum_all["total_row_sum"]
    })

    return JSONResponse(content={"results": results})


@router_crm.get("/report", response_class=HTMLResponse)
async def get_report_page(request: Request,
                          db: Session = Depends(get_db),
                          templates: Jinja2Templates = Depends(lambda: Jinja2Templates(directory="templates"))):
    role = request.session.get("role")
    is_crm = request.session.get("is_crm")
    user_code = request.session.get("user_code")  # کد پرسنلی کاربر فعلی
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    user = db.query(User).filter(User.id == user_id).first()

    return templates.TemplateResponse("user/crm_report.html", {
        "request": request,
        "role": role,
        "is_crm": is_crm,
        "user_code": user_code,
        "user": user

    })
    # return templates.TemplateResponse("user/crm_report.html", {"request": request})


@router_crm.post("/report_crm_excel")
async def report_crm_excel(
        request: Request,
        jalali_date_start: str = Form(...),
        jalali_date_end: str = Form(...),
        code: str = Form(""),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    is_crm = request.session.get("is_crm")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    code = convert_persian_to_english_numbers(code)
    jalali_date_start = convert_persian_to_english_numbers(jalali_date_start)
    jalali_date_end = convert_persian_to_english_numbers(jalali_date_end)

    try:
        start_date = JalaliDate.strptime(jalali_date_start, "%Y/%m/%d").to_gregorian()
        end_date = JalaliDate.strptime(jalali_date_end, "%Y/%m/%d").to_gregorian()
    except:
        raise HTTPException(status_code=400, detail="فرمت تاریخ اشتباه است.")

    if role == "user" and is_crm:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
        code = user.code

    users_query = db.query(User)
    if code:
        users_query = users_query.filter(User.code == code)
    users = users_query.filter(User.is_crm == True).all()

    incoming_fields = [
        "posty_code", "send_product_deadline", "branch_change", "online_change",
        "online_return", "branch_dissatisfaction", "payment_followup", "incomplete_delivery",
        "b2b_sales", "waiting_for_payment", "product_search", "after_sales_service",
        "club", "other"
    ]
    outgoing_fields = ["internet", "voice_mail"]

    headers = [
        "نام", "کد پرسنلی", "رهگیری", "ارسال کالا", "تعویض شعبه", "تعویض آنلاین",
        "مرجوع آنلاین", "نارضایتی شعبه", "پیگیری واریزی", "ارسال ناقص",
        "فروش سازمانی", "در انتظار پرداخت", "سرچ کالا", "پس از فروش",
        "باشگاه", "متفرقه", "پیگیری اینترنتی", "صندوق صوتی", "جمع ردیف"
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "گزارش CRM"
    # فعال کردن راست به چپ برای شیت
    ws.sheet_view.rightToLeft = True



    # نوشتن عنوان ستون‌ها
    ws.append(headers)
    # استایل برای هدرها (پس‌زمینه رنگی + متن بولد + وسط‌چین)
    header_fill = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")
    header_font = Font(bold=True, color="000000")
    header_alignment = Alignment(horizontal="center", vertical="center")
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
    # استایل داده‌ها (راست‌چین + وسط عمودی)
    data_alignment = Alignment(horizontal="center", vertical="center")
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(headers)):
        for cell in row:
            cell.alignment = data_alignment

# تعیین عرض ستون‌ها به صورت اتوماتیک
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = max_length + 2
        ws.column_dimensions[col_letter].width = adjusted_width

    total_sum_all = {field: 0 for field in incoming_fields + outgoing_fields}
    total_sum_all["total_row_sum"] = 0

    for user in users:
        incoming_records = db.query(IncomingCall).filter(
            IncomingCall.user_id == user.id,
            IncomingCall.datetime >= start_date,
            IncomingCall.datetime <= end_date
        ).all()

        out_records = db.query(OutCall).filter(
            OutCall.user_id == user.id,
            OutCall.datetime >= start_date,
            OutCall.datetime <= end_date
        ).all()

        def sum_fields(records, fields):
            return {field: sum(getattr(r, field) or 0 for r in records) for field in fields}

        incoming_data = sum_fields(incoming_records, incoming_fields)
        out_data = sum_fields(out_records, outgoing_fields)

        total_row_sum = sum(incoming_data.values()) + sum(out_data.values())

        # آپدیت مجموع کل
        for field, value in {**incoming_data, **out_data}.items():
            total_sum_all[field] += value
        total_sum_all["total_row_sum"] += total_row_sum

        row = [
                  f"{user.name} {user.family}",
                  user.code
              ] + [incoming_data[field] for field in incoming_fields] + \
              [out_data[field] for field in outgoing_fields] + \
              [total_row_sum]

        ws.append(row)

    # ردیف مجموع کل
    total_row = ["مجموع کل", "-"] + \
                [total_sum_all[field] for field in incoming_fields] + \
                [total_sum_all[field] for field in outgoing_fields] + \
                [total_sum_all["total_row_sum"]]
    ws.append(total_row)

    # محاسبه درصد بر اساس توضیح شما
    total_calls_sum = total_sum_all["total_row_sum"] or 1  # ستون آخر مجموع کل
    percent_row = ["درصد", "-"]

    percent_fill = PatternFill(start_color="C6E0B4", end_color="C6E0B4", fill_type="solid")  # سبز ملایم
    percent_font = Font(bold=True, color="006100")  # سبز تیره

    # ردیف درصد
    total_calls_sum = total_sum_all["total_row_sum"] or 1
    percent_row = ["درصد", "-"]

    for field in incoming_fields + outgoing_fields:
        col_sum = total_sum_all[field] or 0
        percent_value = round((col_sum / total_calls_sum) * 100, 2) if col_sum else 0
        percent_row.append(f"{percent_value}%")  # اضافه کردن علامت %

    percent_row.append("100%")  # ستون آخر همیشه 100%

    ws.append(percent_row)
    for cell in ws[ws.max_row]:
        cell.fill = percent_fill
        cell.font = percent_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # ساخت فایل در حافظه
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"crm_report_{jalali_date_start}_{jalali_date_end}.xlsx"
    response = StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{filename}"
    return response


@router_crm.post("/average_report_crm")
async def average_report_crm(
        request: Request,
        jalali_date_start: str = Form(...),
        jalali_date_end: str = Form(...),
        code: str = Form(""),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    is_crm = request.session.get("is_crm")
    if not user_id:
        return RedirectResponse(url="/", status_code=302)

    code = convert_persian_to_english_numbers(code)
    jalali_date_start = convert_persian_to_english_numbers(jalali_date_start)
    jalali_date_end = convert_persian_to_english_numbers(jalali_date_end)

    try:
        start_date = JalaliDate.strptime(jalali_date_start, "%Y/%m/%d").to_gregorian()
        end_date = JalaliDate.strptime(jalali_date_end, "%Y/%m/%d").to_gregorian()
    except:
        raise HTTPException(status_code=400, detail="فرمت تاریخ اشتباه است.")

    users_query = db.query(User)
    if code:
        users_query = users_query.filter(User.code == code)
    users = users_query.filter(User.is_crm == True).all()

    if not users:
        raise HTTPException(status_code=404, detail="کاربری یافت نشد.")

    results = []

    incoming_fields = [
        "posty_code", "send_product_deadline", "branch_change", "online_change",
        "online_return", "branch_dissatisfaction", "payment_followup", "incomplete_delivery",
        "b2b_sales", "waiting_for_payment", "product_search", "after_sales_service",
        "club", "other"
    ]
    outgoing_fields = ["internet"]

    total_sum_all = {field: 0 for field in incoming_fields + outgoing_fields}
    total_sum_all["total_row_sum"] = 0

    for user in users:
        incoming_records = db.query(IncomingCall).filter(
            IncomingCall.user_id == user.id,
            IncomingCall.datetime >= start_date,
            IncomingCall.datetime <= end_date
        ).all()

        out_records = db.query(OutCall).filter(
            OutCall.user_id == user.id,
            OutCall.datetime >= start_date,
            OutCall.datetime <= end_date
        ).all()

        def sum_fields(records, fields):
            return {field: sum(getattr(r, field) or 0 for r in records) for field in fields}

        incoming_data = sum_fields(incoming_records, incoming_fields)
        out_data = sum_fields(out_records, outgoing_fields)

        total_row_sum = sum(incoming_data.values()) + sum(out_data.values())

        for field, value in {**incoming_data, **out_data}.items():
            total_sum_all[field] += value
        total_sum_all["total_row_sum"] += total_row_sum

        results.append({
            "name": f"{user.name} {user.family}",
            "code": user.code,
            "incoming": incoming_data,
            "out": out_data,
            "total_row_sum": total_row_sum
        })

    # محاسبه میانگین
    user_count = len(users)
    average_data = {
        field: round(value / user_count, 2) for field, value in total_sum_all.items()
    }

    return {
        "user_count": user_count,
        "total_sum_all": total_sum_all,
        "average_per_user": average_data,
        "detailed_results": results
    }
