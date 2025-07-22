from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.orm import relationship

from DB.database import Base

class MeetingRoom(Base):
    __tablename__ = 'meeting_rooms'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)
    capacity =Column(Integer, nullable=True)

    office = relationship("Office", back_populates="meeting_rooms")
    reservations = relationship("MeetingRoomReservation", back_populates="meeting_room")


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
    meeting_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)

    user = relationship("User")
    office = relationship("Office")
    meeting_room = relationship("MeetingRoom", back_populates="reservations")
