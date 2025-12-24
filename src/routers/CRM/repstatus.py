from typing import Optional

import jdatetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from DB.database import get_db
from models.CallEventStatus import CallEventStatus
from models.IncomingCallEvent import IncomingCallEvent
from models.inCall import IncomingCall
from models.user import User

router_crm_rep = APIRouter(tags=["CRM Reports"])
templates = Jinja2Templates(directory="templates")


def jalali_to_gregorian(j_date: str):
    y, m, d = map(int, j_date.split("/"))
    return jdatetime.date(y, m, d).togregorian()


@router_crm_rep.get("/crm_status_rep", response_class=HTMLResponse)
def crm_status_rep(request: Request, db: Session = Depends(get_db)):
    topics = db.query(IncomingCallEvent.topic).distinct().all()
    users = db.query(User).filter(User.is_crm == True).all()

    return templates.TemplateResponse(
        "user/crm_status_report.html",
        {
            "request": request,
            "topics": [t[0] for t in topics],
            "users": users
        }
    )


@router_crm_rep.get("/reports/calls", response_class=JSONResponse)
def call_reports(
        start_date: str,
        end_date: str,
        status: Optional[int] = None,
        topic: Optional[str] = None,
        user_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    start = jalali_to_gregorian(start_date)
    end = jalali_to_gregorian(end_date)

    # Subquery آخرین وضعیت هر تماس
    latest_status_subq = (
        db.query(
            CallEventStatus.call_event_id,
            func.max(CallEventStatus.created_at).label("max_created")
        )
        .group_by(CallEventStatus.call_event_id)
        .subquery()
    )

    LatestStatus = aliased(CallEventStatus)

    query = (
        db.query(
            IncomingCallEvent.topic,
            LatestStatus.status,
            func.count(IncomingCallEvent.id).label("count")
        )
        .join(IncomingCall, IncomingCall.id == IncomingCallEvent.incoming_call_id)
        .join(
            latest_status_subq,
            latest_status_subq.c.call_event_id == IncomingCallEvent.id
        )
        .join(
            LatestStatus,
            (LatestStatus.call_event_id == IncomingCallEvent.id) &
            (LatestStatus.created_at == latest_status_subq.c.max_created)
        )
        .filter(IncomingCall.datetime.between(start, end))
    )

    if status is not None:
        query = query.filter(LatestStatus.status == status)

    if topic:
        query = query.filter(IncomingCallEvent.topic == topic)

    if user_id:
        query = query.filter(IncomingCallEvent.user_id == user_id)

    query = query.group_by(
        IncomingCallEvent.topic,
        LatestStatus.status
    )

    return [
        {
            "topic": r.topic,
            "status": r.status,
            "count": r.count
        }
        for r in query.all()
    ]
