from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin_dashboard")
def admin_dashboard(request: Request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("admin/admin_dashboard.html", {
        "request": request,

    })
