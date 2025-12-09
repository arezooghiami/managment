from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from DB.database import Base


class Branch(Base):
    __tablename__ = 'branches'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, comment="نام شعبه")

    regional_manager_id = Column(
        Integer,
        ForeignKey("regional_managers.id"),
        nullable=True,
        comment="مدیر منطقه شعبه"
    )

    regional_manager = relationship("RegionalManager", back_populates="branches")


class Unit(Base):
    __tablename__ = 'units'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, comment="نام واحد سازمانی")
