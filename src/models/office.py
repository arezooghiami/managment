from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from DB.database import Base



class Office(Base):
    __tablename__ = "offices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # مثلاً "دفتر مشهد"، "دفتر تهران"
    meeting_rooms = relationship("MeetingRoom", back_populates="office")
