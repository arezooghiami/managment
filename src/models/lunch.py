
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from DB.database import Base
from datetime import date





class LunchMenu(Base):
    __tablename__ = 'lunch_menus'

    id = Column(Integer, primary_key=True, index=True)
    weekday = Column(String, nullable=False)
    date = Column(Date, nullable=False, unique=False)
    main_dish = Column(String, nullable=False)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=False)

    office = relationship("Office")



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