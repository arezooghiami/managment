from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from DB.database import Base


class RegionalManager(Base):
    __tablename__ = 'regional_managers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, comment="نام مدیر منطقه")

    # رابطه با شعبات
    branches = relationship("Branch", back_populates="regional_manager")
