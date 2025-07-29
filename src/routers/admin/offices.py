from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.orm import Session, joinedload
from starlette.responses import RedirectResponse, HTMLResponse
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.meet import MeetingRoom
from models.office import Office

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/offices", response_class=HTMLResponse)
async def office_management(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    office_id = request.session.get("office_id")

    # if not user_id or role != "admin":
    if not user_id or role != 'admin' or office_id != 1:
        return RedirectResponse(url="/", status_code=302)

    offices = db.query(Office).all()
    meeting_room = db.query(MeetingRoom).options(joinedload(MeetingRoom.office)).all()

    return templates.TemplateResponse("admin/offices.html", {
        "request": request,
        "offices": offices,
        "meeting_room": meeting_room,
    })


@router.post("/admin/add_office", response_class=HTMLResponse)
async def add_office(
        request: Request,
        office_name: str = Form(...),
        address: str = Form(...),
        db: Session = Depends(get_db)
):
    office = db.query(Office).filter(Office.name == office_name).first()
    if office:
        request.session["flash"] = "دفتر انتخاب شده وجود دارد"
        return RedirectResponse(url="/admin/offices", status_code=303)
    new_office = Office(
        name=office_name,
        address=address,

    )

    db.add(new_office)
    db.commit()

    request.session["flash"] = " با موفقیت افزوده شد"
    return RedirectResponse(url="/admin/offices", status_code=303)


@router.post("/admin/add_meetingroom", response_class=HTMLResponse)
async def add_meetingroom(
        request: Request,
        name: str = Form(...),
        capacity: int = Form(...),
        office_id: int = Form(...),
        db: Session = Depends(get_db)
):
    meetingroom = db.query(MeetingRoom).filter(
        MeetingRoom.office_id == office_id,
        MeetingRoom.name == name
    ).first()
    if meetingroom:
        request.session["flash"] = "اتاق جلسه با این مشخصات قبلاً ثبت شده است"
        return RedirectResponse(url="/admin/offices", status_code=303)
    new_meetingroom = MeetingRoom(
        name=name,
        office_id=office_id,
        capacity=capacity

    )

    db.add(new_meetingroom)
    db.commit()

    request.session["flash"] = " با موفقیت افزوده شد"
    return RedirectResponse(url="/admin/offices", status_code=303)


@router.post("/admin/delete_office", response_class=HTMLResponse)
async def delete_office(request: Request, office_id: int = Form(...), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    session_office_id = request.session.get("office_id")  # برای بررسی دسترسی

    if not user_id or role != 'admin' or session_office_id != 1:
        return RedirectResponse(url="/", status_code=302)

    office = db.query(Office).filter(Office.id == office_id).first()

    if not office:
        request.session["flash"] = "دفتر یافت نشد"
        return RedirectResponse(url="/admin/offices", status_code=303)

    db.delete(office)
    db.commit()
    request.session["flash"] = "دفتر با موفقیت حذف شد"
    return RedirectResponse(url="/admin/offices", status_code=303)
@router.post("/admin/delete_meetingroom", response_class=HTMLResponse)
async def delete_meetingroom(request: Request, meetingroom_id: int = Form(...), db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    session_office_id = request.session.get("office_id")

    if not user_id or role != 'admin' or session_office_id != 1:
        return RedirectResponse(url="/", status_code=302)

    meetingroom = db.query(MeetingRoom).filter(MeetingRoom.id == meetingroom_id).first()

    if not meetingroom:
        request.session["flash"] = "اتاق جلسه یافت نشد"
        return RedirectResponse(url="/admin/offices", status_code=303)

    db.delete(meetingroom)
    db.commit()
    request.session["flash"] = "اتاق جلسه با موفقیت حذف شد"
    return RedirectResponse(url="/admin/offices", status_code=303)