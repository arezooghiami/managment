from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates



router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin_dashboard")
def admin_dashboard(request: Request):


    return templates.TemplateResponse("admin/admin_dashboard.html", {"request": request})
