from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time,DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, date
from DB.database import Base
class IncomingCallEvent(Base):
    __tablename__ = "incoming_call_events"

    id = Column(Integer, primary_key=True)

    incoming_call_id = Column(
        Integer,
        ForeignKey("incoming_calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    topic = Column(
        String(50),
        nullable=False,
        index=True,
        comment="send_product_deadline, branch_change, ..."
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    statuses = relationship(
        "CallEventStatus",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="CallEventStatus.created_at"
    )


    incoming_call = relationship("IncomingCall", back_populates="events")
