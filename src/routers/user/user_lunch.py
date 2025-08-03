from datetime import date, timedelta
from datetime import datetime, time
from typing import Optional

import jdatetime
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.lunch import LunchMenu, LunchOrder
from models.user import User

router_user_lunch = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_jalali_weekday(g_date):
    j_date = jdatetime.date.fromgregorian(date=g_date)
    weekdays = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
    return weekdays[j_date.weekday()]


def to_jalali(gdate):
    return jdatetime.date.fromgregorian(date=gdate).strftime('%Y/%m/%d')


@router_user_lunch.get("/user_dashboard/lunch")
async def user_lunch(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    office_id = request.session.get("office_id")
    role = request.session.get("role")

    if not user_id or role != 'user':
        return RedirectResponse(url="/", status_code=302)

    # بررسی وجود کاربر
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now()
    cutoff_time = time(10, 0)
    today = date.today()

    # دریافت منوهای آینده از امروز به بعد
    menus = db.query(LunchMenu).filter(
        LunchMenu.date >= today,
        LunchMenu.office_id == office_id
    ).order_by(LunchMenu.date.asc()).all()

    # دریافت تمام سفارش‌های کاربر از امروز به بعد
    orders = db.query(LunchOrder).filter(
        LunchOrder.user_id == user_id,
        LunchOrder.order_date >= today
    ).all()

    # بررسی وجود سفارش برای امروز و فردا
    user_order_today = db.query(LunchOrder).filter(
        LunchOrder.user_id == user_id,
        LunchOrder.order_date == today
    ).first()

    user_order_tomorrow = db.query(LunchOrder).filter(
        LunchOrder.user_id == user_id,
        LunchOrder.order_date == today + timedelta(days=1)
    ).first()

    # تبدیل تاریخ‌ها به شمسی برای منوها
    menus_with_jalali = []
    for menu in menus:
        menu_dict = menu.__dict__.copy()
        menu_dict["jalali_date"] = to_jalali(menu.date)
        menu_dict["jalali_weekday"] = get_jalali_weekday(menu.date)  # ✅ اضافه کردن روز هفته
        menu_dict["can_order"] = now.time() < cutoff_time if menu.date == today else True
        menus_with_jalali.append(menu_dict)

    # تبدیل تاریخ‌ها به شمسی برای سفارش‌ها
    orders_with_jalali = []

    for order in orders:
        order_dict = order.__dict__.copy()
        order_dict["jalali_date"] = to_jalali(order.order_date)

        if order.order_date == today:
            order_dict["can_delete"] = now.time() < cutoff_time
        else:
            order_dict["can_delete"] = True

        orders_with_jalali.append(order_dict)

    # اضافه کردن پیام‌ها در صورت نبود منو یا سفارش
    if not menus:
        request.session.setdefault("messages", []).append("منویی برای نمایش وجود ندارد.")
    if not orders:
        request.session.setdefault("messages", []).append("سفارشی برای ناهار ثبت نشده است.")

    return templates.TemplateResponse("user/user_lunch.html", {
        "request": request,
        "user": user,
        "lunch_menu": menus_with_jalali,
        "orders": orders_with_jalali,
        "user_order_today": user_order_today,
        "user_order_tomorrow": user_order_tomorrow,
        "now": now,
        "cutoff_time": cutoff_time
    })


@router_user_lunch.post("/order_lunch")
def order_lunch(
        request: Request,
        user_id: int = Form(...),
        menu_id: int = Form(...),
        selected_dish: str = Form(...),
        description: str = Form(...),
        for_guest: Optional[str] = Form(None),
        guest_name: Optional[str] = Form(None),
        guest_company: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    now = datetime.now()
    cutoff_time = time(10, 0)

    # گرفتن منوی انتخاب شده
    menu = db.query(LunchMenu).filter(LunchMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="منوی انتخاب‌شده یافت نشد.")

    order_date = menu.date

    # ⛔ جلوگیری از سفارش برای امروز بعد از ساعت ۱۰
    if order_date == date.today() and now.time() >= cutoff_time:
        request.session.setdefault("messages", []).append(
            f"مهلت ثبت یا ویرایش سفارش ناهار امروز ({to_jalali(order_date)}) به پایان رسیده است."
        )
        return RedirectResponse(url="/user_dashboard/lunch", status_code=302)

    # ساخت اطلاعات کامل مهمان
    full_guest_info = f"{guest_name} - {guest_company}" if guest_name else None

    if for_guest == "on" and guest_name:
        # ثبت سفارش برای مهمان
        new_order = LunchOrder(
            user_id=user_id,
            lunch_menu_id=menu_id,
            selected_dish=selected_dish,
            order_date=order_date,
            guest_name=full_guest_info,
            description=description
        )
        db.add(new_order)
        message = f"سفارش ناهار برای مهمان «{guest_name}» با موفقیت ثبت شد."
    else:
        # بررسی وجود سفارش قبلی برای همین روز و همین کاربر (نه مهمان)
        existing_order = db.query(LunchOrder).filter(
            LunchOrder.user_id == user_id,
            LunchOrder.order_date == order_date,
            LunchOrder.guest_name == None
        ).first()

        if existing_order:
            existing_order.lunch_menu_id = menu_id
            existing_order.selected_dish = selected_dish
            existing_order.description = description
            message = f"سفارش ناهار شما برای تاریخ {to_jalali(order_date)} ویرایش شد."
        else:
            new_order = LunchOrder(
                user_id=user_id,
                lunch_menu_id=menu_id,
                selected_dish=selected_dish,
                order_date=order_date,
                description=description
            )
            db.add(new_order)
            message = f"سفارش ناهار شما برای تاریخ {to_jalali(order_date)} با موفقیت ثبت شد."

    db.commit()

    # افزودن پیام به سشن
    request.session.setdefault("messages", []).append(message)

    return RedirectResponse(url="/user_dashboard/lunch", status_code=302)


# @router_user_lunch.post("/order_lunch")
# def order_lunch(
#         request: Request,
#         user_id: int = Form(...),
#         menu_id: int = Form(...),
#         selected_dish: str = Form(...),
#         description: str = Form(...),
#         for_guest: Optional[str] = Form(None),
#         guest_name: Optional[str] = Form(None),
#         db: Session = Depends(get_db)
# ):
#     # order_date = date.today() + timedelta(days=1)
#     now = datetime.now()
#     cutoff_time = time(10, 0)
#
#     # منطق بررسی زمان برای سفارش امروز یا فردا
#     if now.time() < cutoff_time:
#         order_date = date.today()
#     else:
#         order_date = date.today() + timedelta(days=1)
#
#     if for_guest == "on" and guest_name:
#         # سفارش جدید برای مهمان
#         new_order = LunchOrder(
#             user_id=user_id,
#             lunch_menu_id=menu_id,
#             selected_dish=selected_dish,
#             order_date=order_date,
#             guest_name=guest_name,
#             description=description
#         )
#         db.add(new_order)
#         message = f"سفارش برای مهمان {guest_name} ثبت شد."
#     else:
#         # فقط یک سفارش در روز برای خود شخص قابل ویرایش است
#         existing_order = db.query(LunchOrder).filter(
#             LunchOrder.user_id == user_id,
#             LunchOrder.order_date == order_date,
#             LunchOrder.guest_name == None
#         ).first()
#
#         if existing_order:
#             existing_order.lunch_menu_id = menu_id
#             existing_order.selected_dish = selected_dish
#             existing_order.description = description
#             message = "سفارش ناهار شما ویرایش شد."
#         else:
#             new_order = LunchOrder(
#                 user_id=user_id,
#                 lunch_menu_id=menu_id,
#                 selected_dish=selected_dish,
#                 order_date=order_date,
#                 description=description
#             )
#             db.add(new_order)
#             message = "سفارش ناهار شما ثبت شد."
#
#     db.commit()
#     if for_guest == "on" and guest_name:
#
#         message = f"سفارش ناهار برای مهمان «{guest_name}» با موفقیت ثبت شد."
#     else:
#
#         message = "سفارش ناهار شما با موفقیت ثبت شد."
#
#     if "messages" not in request.session:
#         request.session["messages"] = []
#
#     request.session["messages"].append(message)
#     return RedirectResponse(url=f"/user_dashboard/lunch", status_code=302)


@router_user_lunch.post("/delete_guest_order/{order_id}")
def delete_guest_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    # بررسی وجود user_id و نقش کاربر
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != 'user':
        request.session.setdefault("messages", []).append("خطا: لطفاً ابتدا وارد شوید.")
        return RedirectResponse(url="/", status_code=302)

    # بررسی وجود کاربر
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        request.session.setdefault("messages", []).append("خطا: کاربر یافت نشد.")
        return RedirectResponse(url="/user_dashboard/lunch", status_code=302)

    # پیدا کردن سفارش مهمان
    guest_order = db.query(LunchOrder).filter(
        LunchOrder.id == order_id,
        LunchOrder.user_id == user_id,
        LunchOrder.guest_name != None  # استفاده از guest_name به‌جای for_guest
    ).first()

    if not guest_order:
        request.session.setdefault("messages", []).append("خطا: سفارش مهمان یافت نشد یا اجازه حذف آن را ندارید.")
        return RedirectResponse(url="/user_dashboard/lunch", status_code=302)

    # بررسی تاریخ سفارش برای جلوگیری از حذف سفارش‌های گذشته
    now = datetime.now()
    cutoff_time = time(10, 0)
    today = date.today()
    if guest_order.order_date < today:
        request.session.setdefault("messages", []).append("خطا: نمی‌توانید سفارش‌های گذشته را حذف کنید.")
        return RedirectResponse(url="/user_dashboard/lunch", status_code=302)

    try:
        db.delete(guest_order)
        db.commit()
        jalali_date = to_jalali(guest_order.order_date)
        request.session.setdefault("messages", []).append(
            f"سفارش مهمان «{guest_order.guest_name}» برای تاریخ {jalali_date} با موفقیت حذف شد."
        )
    except Exception as e:
        db.rollback()
        request.session.setdefault("messages", []).append(f"خطا در حذف سفارش: {str(e)}")
        return RedirectResponse(url="/user_dashboard/lunch", status_code=302)

    return RedirectResponse(url="/user_dashboard/lunch", status_code=302)


@router_user_lunch.post("/delete_user_order/{order_id}")
def delete_user_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(LunchOrder).filter(LunchOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()
    return RedirectResponse(url="/user_dashboard/lunch", status_code=302)
