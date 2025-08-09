from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time
from sqlalchemy.orm import relationship

from DB.database import Base
class OutCall(Base):
    __tablename__ = 'out_calls'  # اسم بهتر برای جمع بودن

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    internet = Column(Integer, comment="خروجی پیگیری اینترنتی")
    datetime = Column(Date)
