import os
import logging
from logging.handlers import TimedRotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
import jdatetime
import pytz
from datetime import datetime
import uvicorn
from dotenv import load_dotenv

# ── مدل‌ها و دیتابیس ────────────────────────────────────────
from models import office
from DB.database import Base, engine
from routers.Athentication.addSuperAdmin import register_superadmin

# ── روترها ───────────────────────────────────────────────────
from routers.Athentication.api import login
from routers.CRM import crm
from routers.CRM.complaint.complaint import router_complaint
from routers.CRM.complaint.import_data import router_branch, router_issues, router_managers, router_unit
from routers.CRM.repstatus import router_crm_rep
from routers.admin import (
    admin_dashboard, lunch, excel, meeting_room, report, user_managment, offices, room_lock
)
from routers.user import (
    user_dashboard, user_lunch, user_meetingroom, user_notification, user_changepass
)

# فقط یک بار ایجاد اپلیکیشن
app = FastAPI()
data_dir = ".data"
logs_dir = os.path.join(data_dir, "logs")

os.makedirs(logs_dir, exist_ok=True)  # اگر وجود نداشت، بساز

# حالا می‌توانیم لاگر را بسازیم
file_handler = TimedRotatingFileHandler(
    os.path.join(logs_dir, "user_actions.log"),
    when="D",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
# تنظیم لاگر (فقط یک بار)
user_logger = logging.getLogger("user_actions")
user_logger.setLevel(logging.INFO)

if not user_logger.handlers:
    file_handler = TimedRotatingFileHandler(
        ".data/logs/user_actions.log",
        when="D",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-5s | %(user_id)-12s | %(method)-6s | %(ip)-15s | %(url)s | %(user_agent)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    user_logger.addHandler(file_handler)
    user_logger.propagate = False

# Middleware لاگ درخواست‌ها
@app.middleware("http")
async def log_requests(request: Request, call_next):
    user_id = request.session.get("user_id", "Anonymous") if hasattr(request, "session") else "Anonymous"

    response = await call_next(request)

    extra = {
        "user_id": user_id,
        "method": request.method,
        "url": str(request.url),
        "ip": request.client.host or "unknown",
        "user_agent": request.headers.get("user-agent", "unknown")
    }

    user_logger.info(f"status={response.status_code}", extra=extra)
    return response

# تنظیمات جلسات
app.add_middleware(
    SessionMiddleware,
    secret_key="e455a74e1805ab61e6c1a9c57ee4e5c2a6d64dfe6e97c3753fe5723dc7a8f670",
    session_cookie="session",
    max_age=18000,
    same_site="lax"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# اتصال استاتیک فایل‌ها
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# تنظیم Jinja2 + فیلترها و گلوبال‌ها
templates = Jinja2Templates(directory="templates")

def get_today_jalali_iran():
    iran_tz = pytz.timezone("Asia/Tehran")
    iran_now = datetime.now(iran_tz)
    jalali_now = jdatetime.datetime.fromgregorian(datetime=iran_now)
    return jalali_now.strftime('%Y/%m/%d')

def to_jalali(value):
    if value:
        return jdatetime.datetime.fromgregorian(datetime=value).strftime("%Y/%m/%d")
    return ""

templates.env.globals["get_today_jalali_iran"] = get_today_jalali_iran
templates.env.filters["to_jalali"] = to_jalali

# اضافه کردن روترها
app.include_router(login.router_login)
app.include_router(admin_dashboard.router)
app.include_router(lunch.router_lunch)
app.include_router(excel.router_excel)
app.include_router(user_dashboard.router_user)
app.include_router(meeting_room.router)
app.include_router(report.router_report)
app.include_router(user_lunch.router_user_lunch)
app.include_router(user_meetingroom.router_user)
app.include_router(user_managment.router)
app.include_router(offices.router)
app.include_router(room_lock.router_admin)
app.include_router(user_notification.router_user)
app.include_router(crm.router_crm)
app.include_router(user_changepass.router_user)
app.include_router(router_branch)
app.include_router(router_issues)
app.include_router(router_managers)
app.include_router(router_complaint)
app.include_router(router_unit)
app.include_router(router_crm_rep)


def initialize_database():
    Base.metadata.create_all(bind=engine)
    register_superadmin()


if __name__ == "__main__":
    # ایجاد جداول و سوپرادمین قبل از ران شدن سرور
    initialize_database()
    load_dotenv()

    host = "0.0.0.0"
    port = 5300
    uvicorn.run(app, host=host, port=port)