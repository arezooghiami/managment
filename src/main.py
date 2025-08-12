import os
from fastapi.templating import Jinja2Templates
import jdatetime
import pytz
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from jinja2 import Environment, FileSystemLoader
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from models import office
from DB.database import Base, engine
from routers.Athentication.addSuperAdmin import register_superadmin
from routers.Athentication.api import login
from routers.CRM import crm
from routers.admin import admin_dashboard, lunch, excel, meeting_room, report, user_managment, offices, room_lock
from routers.user import user_dashboard, user_lunch, user_meetingroom, user_notification, user_changepass

env = Environment(loader=FileSystemLoader('templates'))



def get_today_jalali_iran():
    iran_tz = pytz.timezone("Asia/Tehran")
    iran_now = datetime.now(iran_tz)
    jalali_now = jdatetime.datetime.fromgregorian(datetime=iran_now)
    return jalali_now.strftime('%Y/%m/%d')


templates = Jinja2Templates(directory="templates")
templates.env.globals["get_today_jalali_iran"] = get_today_jalali_iran

app = FastAPI()
host = "0.0.0.0"
port = 5300

app.add_middleware(SessionMiddleware, secret_key="e455a74e1805ab61e6c1a9c57ee4e5c2a6d64dfe6e97c3753fe5723dc7a8f670",
                   session_cookie="session",max_age=18000, same_site="lax")


app.include_router(login.router_login)
# app.include_router(admin_login.router_admin)
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


def initialize_database():
    Base.metadata.create_all(bind=engine)
    register_superadmin()
    # import_users()  # Create tables


initialize_database()

load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to be more specific in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates_dir = "templates"
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

# Initialize Jinja2Templates
templates = Jinja2Templates(directory=templates_dir)

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
