
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from DB.database import Base
from datetime import date


class Lunch(Base):
    __tablename__ = "lunches"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)



class LunchMenu(Base):
    __tablename__ = 'lunch_menus'

    id = Column(Integer, primary_key=True, index=True)
    weekday = Column(String, nullable=False)  # مثل: یکشنبه، دوشنبه
    date = Column(Date, nullable=False, unique=True)
    main_dish = Column(String, nullable=False)



class LunchOrder(Base):
    __tablename__ = 'lunch_orders'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lunch_menu_id = Column(Integer, ForeignKey("lunch_menus.id"), nullable=False)
    order_date = Column(Date, nullable=False)
    selected_dish = Column(String, nullable=True)
    guest_name = Column(String, nullable=True)

    user = relationship("User")
    lunch_menu = relationship("LunchMenu")