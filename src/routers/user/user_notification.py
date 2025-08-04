from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from DB.database import get_db
from models.notification import Notification

router_user = APIRouter()
templates = Jinja2Templates(directory="templates")


class MarkNotificationReadRequest(BaseModel):
    notification_id: int


@router_user.post("/user/mark_notification_read")
def mark_notification_read(
        data: MarkNotificationReadRequest,
        db: Session = Depends(get_db)
):
    notification = db.query(Notification).filter(Notification.id == data.notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()

    return {"success": True}
