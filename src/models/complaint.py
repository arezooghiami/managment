from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
from DB.database import Base

class CustomerComplaint(Base):
    __tablename__ = 'customer_complaints'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="کاربر CRM ثبت‌کننده")
    customer_name = Column(String, nullable=False, comment="نام مشتری")
    customer_phone = Column(String, nullable=False, comment="شماره تماس مشتری")

    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, comment="شعبه مربوطه")
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, comment="واحد سازمانی مربوطه")
    regional_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="مدیر منطقه مربوطه")

    issues = Column(ARRAY(Integer), nullable=False, comment="آرایه‌ای از آی‌دی‌های شکایات انتخاب شده")
    description = Column(Text, nullable=True, comment="توضیحات تکمیلی")

    # status = Column(String, default="جدید", comment="وضعیت شکایت")
    tracking_code = Column(String, unique=True, nullable=False, comment="کد رهگیری یونیک")

    created_at = Column(DateTime, default=datetime.utcnow, comment="تاریخ و ساعت ثبت")

    # ارتباط‌ها
    user = relationship("User", foreign_keys=[user_id], backref="complaints")
    branch = relationship("Branch", backref="complaints")
    unit = relationship("Unit", backref="complaints")
    regional_manager = relationship("User", foreign_keys=[regional_manager_id], backref="complaints_as_manager")
