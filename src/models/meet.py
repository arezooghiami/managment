from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.orm import relationship

from DB.database import Base


class MeetingRoomReservation(Base):
    __tablename__ = 'meeting_room_reservations'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reservation_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    participants = Column(Integer, nullable=False)
    subject = Column(String, nullable=True)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)

    user = relationship("User")
    office = relationship("Office")

