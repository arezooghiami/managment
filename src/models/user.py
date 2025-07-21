from sqlalchemy import Column, Integer, String, ForeignKey, Date, Text
from sqlalchemy import Enum
from sqlalchemy.orm import relationship

from DB.database import Base
from schemas.user import UserRole


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    family =Column(String(50), nullable=False)
    code = Column(String, unique=True, index=True)
    role = Column(Enum(UserRole), nullable=False)   #admin, user
