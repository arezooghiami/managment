from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time,DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, date
from DB.database import Base

class CallEventStatus(Base):
    __tablename__ = "call_event_statuses"

    id = Column(Integer, primary_key=True)

    call_event_id = Column(
        Integer,
        ForeignKey("incoming_call_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    event = relationship("IncomingCallEvent", back_populates="statuses")
