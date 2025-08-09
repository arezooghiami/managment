from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text,Boolean
from sqlalchemy import Enum
from sqlalchemy.orm import relationship

from DB.database import Base
from schemas.user import UserRole, Status


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    family = Column(String(50), nullable=False)
    code = Column(String, unique=True, index=True)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)  # admin, user
    status = Column(Enum(Status), nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)
    is_crm = Column(Boolean, default=False, nullable=False)

    office = relationship("Office", back_populates="users")
