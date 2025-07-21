import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates


from DB.database import Base, engine
from routers.Athentication.api import login, admin_register
from jinja2 import Environment, FileSystemLoader

from routers.admin import admin_dashboard, lunch,excel,meeting_room, report
from routers.user import user_dashboard

env = Environment(loader=FileSystemLoader('templates'))
import secrets

app = FastAPI()
host = "0.0.0.0"
port = 5300

app.add_middleware(SessionMiddleware, secret_key="e455a74e1805ab61e6c1a9c57ee4e5c2a6d64dfe6e97c3753fe5723dc7a8f670")

app.include_router(login.router_login)
# app.include_router(admin_login.router_admin)
app.include_router(admin_dashboard.router)
app.include_router(lunch.router_lunch)
app.include_router(excel.router_excel)
app.include_router(user_dashboard.router_user)
app.include_router(meeting_room.router)
app.include_router(report.router)

def initialize_database():
    Base.metadata.create_all(bind=engine)
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
static_dir = "../static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount(
    "/static",
    StaticFiles(directory="/Users/arezooghiami/Desktop/ML_managment/static"),
    name="static"
)
templates_dir = "templates"
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

# Initialize Jinja2Templates
templates = Jinja2Templates(directory=templates_dir)

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
