from datetime import date, timedelta
from datetime import datetime
from typing import List, Optional

import jdatetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi import Form
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse, JSONResponse

from DB.database import get_db
from models.lunch import LunchMenu, LunchOrder
from models.user import User

router_lunch = APIRouter(prefix="/lunch", tags=["lunch"])

TEMPLATES_DIR = "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def can_order_lunch(order_date: date) -> bool:
    now = datetime.now()
    deadline = datetime.combine(order_date - timedelta(days=1), datetime.strptime("20:00", "%H:%M").time())
    return now <= deadline


# محاسبه تاریخ‌های هفته
def get_week_dates(start_date: date) -> list[date]:
    week_start = start_date - timedelta(days=start_date.weekday())  # شروع هفته (شنبه)
    return [week_start + timedelta(days=i) for i in range(6)]  # شنبه تا پنج‌شنبه


def get_current_week_dates() -> List[date]:
    today = date.today()
    weekday = today.weekday()  # 0=Monday, ..., 6=Sunday
    start_delta = (weekday + 2) % 7  # فاصله تا شنبه
    saturday = today - timedelta(days=start_delta)
    return [saturday + timedelta(days=i) for i in range(6)]  # شنبه تا پنج‌شنبه


@router_lunch.get("/admin/menu")
async def manage_lunch_menu(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    week_dates = get_current_week_dates()  # [شنبه تا پنجشنبه]

    user_id = request.session.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    menus = db.query(LunchMenu).filter(LunchMenu.office_id == user.office_id)

    persian_weekdays = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه"]

    menu_data = {d.strftime("%Y-%m-%d"): None for d in week_dates}

    for menu in menus:
        menu_data[menu.date.strftime("%Y-%m-%d")] = {
            "id": menu.id,
            "weekday": menu.weekday,
            "main_dish": menu.main_dish,

        }

    for menu in menus:
        menu_data[menu.date.strftime("%Y-%m-%d")] = {
            "id": menu.id,
            "weekday": menu.weekday,
            "main_dish": menu.main_dish,
            "office_id": user.office_id

        }
    persian_weekdays = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه"]
    persian_months = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]

    formatted_menu = []
    for i in range(6):  # شنبه تا پنج‌شنبه
        greg_date = week_dates[i]
        j_date = jdatetime.date.fromgregorian(date=greg_date)
        jalali_date = f"{persian_weekdays[i]} {j_date.day} {persian_months[j_date.month - 1]}"
        formatted_menu.append({
            "date": greg_date,
            "jalali_date": jalali_date,
            "weekday": persian_weekdays[i],
            "menu": menu_data[greg_date.strftime("%Y-%m-%d")]
        })

    # # قالب‌دهی برای html
    # formatted_menu = []
    # for i in range(6):  # شنبه تا پنج‌شنبه
    #     greg_date = week_dates[i]
    #     jalali_date = jdatetime.date.fromgregorian(date=greg_date).strftime("%A %d %B")
    #     formatted_menu.append({
    #         "date": greg_date,
    #         "jalali_date": jalali_date,
    #         "weekday": persian_weekdays[i],
    #         "menu": menu_data[greg_date.strftime("%Y-%m-%d")]
    #     })

    return templates.TemplateResponse(
        "admin/admin_menu.html",
        {
            "request": request,
            "menus": formatted_menu,
            "week_dates": week_dates
        }
    )

@router_lunch.post("/admin/add_lunch_menu_single")
def add_lunch_menu_single(
        request: Request,
        date: str = Form(...),
        main_dish: str = Form(...),
        db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()

    persian_weekdays = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]

    weekday_num = (date_obj.weekday() + 2) % 7
    weekday_fa = persian_weekdays[weekday_num]
    user_id = request.session.get("user_id")
    menus = db.query(LunchMenu).filter(LunchMenu.office_id == user_id)
    user = db.query(User).filter(User.id == user_id).first()

    # existing = db.query(LunchMenu).filter(LunchMenu.date == date_obj).first()
    existing = db.query(LunchMenu).filter(LunchMenu.date == date_obj, LunchMenu.office_id == user.office_id).first()

    if existing:
        request.session.setdefault("messages", []).append("برای این روز قبلاً منو ثبت شده است.")
        return RedirectResponse("/admin/add_lunch_menu", status_code=302)

    new_menu = LunchMenu(
        date=date_obj,
        weekday=weekday_fa,
        main_dish=main_dish,
        office_id=user.office_id
    )
    db.add(new_menu)
    db.commit()

    db.refresh(new_menu)
    return RedirectResponse(url=f"/lunch/admin/menu", status_code=302)


class UpdateMenuSchema(BaseModel):
    main_dish: Optional[str] = None
    date: Optional[date] = None
    weekday: Optional[str] = None


@router_lunch.put("/admin/menu/{menu_id}")
def update_menu(menu_id: int, update_data: UpdateMenuSchema, db: Session = Depends(get_db)):
    menu = db.query(LunchMenu).filter(LunchMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="آیتم منو پیدا نشد")

    if update_data.main_dish is not None:
        old_dishes = set(d.strip() for d in menu.main_dish.split('/'))
        new_dishes = set(d.strip() for d in update_data.main_dish.split('/'))
        removed_dishes = old_dishes - new_dishes

        if removed_dishes:
            # بررسی اینکه آیا کسی غذایی از removed_dishes انتخاب کرده
            existing_orders = db.query(LunchOrder).filter(
                LunchOrder.lunch_menu_id == menu_id,
                LunchOrder.selected_dish.in_(removed_dishes)
            ).all()

            if existing_orders:
                used_dishes = set(order.selected_dish for order in existing_orders)
                return JSONResponse(
                    status_code=200,
                    content={
                        "message": f"نمی‌توان منو را ویرایش کرد، زیرا غذای '{removed_dishes}' توسط کاربر انتخاب شده است.",
                        "success": False
                    }
                )

        # مجازه به ویرایش
        menu.main_dish = update_data.main_dish

    if update_data.date is not None:
        menu.date = update_data.date
    if update_data.weekday is not None:
        menu.weekday = update_data.weekday

    db.commit()
    db.refresh(menu)
    return JSONResponse(status_code=200, content={"message": "آیتم با موفقیت ویرایش شد", "success": True})

# # API حذف آیتم منو
# @router_lunch.delete("/admin/menu/{id}")
# async def delete_menu_item(id: int, db: Session = Depends(get_db)):
#
#     menu_item = db.query(LunchMenu).filter(LunchMenu.id == id).first()
#     if not menu_item:
#         raise HTTPException(status_code=404, detail="آیتم منو یافت نشد")
#
#     db.delete(menu_item)
#     db.commit()
#     return {"message": "آیتم منو با موفقیت حذف شد"}
#

# @router_lunch.put("/lunch/admin/menu/{id}")
# async def update_menu_item(id: int, update_data: UpdateMenuSchema, db: Session = Depends(get_db)):
#     # if current_user.role != "admin":
#     #     raise HTTPException(status_code=403, detail="فقط ادمین‌ها می‌توانند منو را ویرایش کنند")
#
#     menu = db.query(LunchMenu).filter(LunchMenu.id == id).first()
#     if not menu:
#         raise HTTPException(status_code=404, detail="آیتم منو پیدا نشد")
#
#     menu.main_dish = update_data.main_dish
#     if update_data.weekday:  # فقط اگر weekday ارسال شده باشد
#         menu.weekday = update_data.weekday
#     menu.updated_at = datetime.now()
#     db.commit()
#     db.refresh(menu)
#     return {"message": "آیتم با موفقیت ویرایش شد"}
# @router_lunch.get("/admin/report")
# def lunch_report(request: Request, report_date: date, db: Session = Depends(get_db)):
#     user_code = request.cookies.get("user_code")
#     if not user_code:
#         return RedirectResponse(url="/", status_code=302)
#
#     user = db.query(User).filter(User.code == user_code).first()
#     if not user or user.role != UserRole.admin:
#         raise HTTPException(status_code=403, detail="فقط ادمین‌ها می‌توانند گزارش ببینند")
#
#     orders = db.query(LunchOrder).filter(LunchOrder.order_date == report_date).all()
#     return templates.TemplateResponse(
#         "lunch_report.html",
#         {"request": request, "orders": orders, "report_date": report_date}
#     )
