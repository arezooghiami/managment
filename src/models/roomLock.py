from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.orm import relationship

from DB.database import Base


class RoomLock(Base):
    __tablename__ = "room_locks"

    id = Column(Integer, primary_key=True)
    meeting_room_id = Column(Integer, ForeignKey("meeting_rooms.id"))
    office_id = Column(Integer, ForeignKey("offices.id"))  # اختیاری
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time)
    end_time = Column(Time)
    reason = Column(String)

    meeting_room = relationship("MeetingRoom")
