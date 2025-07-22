from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from starlette.templating import Jinja2Templates



router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin_dashboard")
def admin_dashboard(request: Request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    office_id = request.session.get("office_id")

    if not user_id or role != "admin":
        return RedirectResponse(url="/", status_code=302)

    # حالا فقط اطلاعات مربوط به همون office
    # menu_items = db.query(Menu).filter(Menu.office_id == office_id).all()

    return templates.TemplateResponse("admin/admin_dashboard.html", {
        "request": request,

    })
