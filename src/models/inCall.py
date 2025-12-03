from sqlalchemy import Column, Integer, String, ForeignKey, Date, Time,DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, date
from DB.database import Base

class IncomingCall(Base):
    __tablename__ = 'incoming_calls'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    posty_code = Column(Integer, comment="استعلام کد رهگیری")
    send_product_deadline = Column(Integer, comment="مهلت ارسال کالا")

    branch_change = Column(Integer, comment="تعویض شعبه")
    online_change = Column(Integer, comment="تعویض آنلاین")
    online_return = Column(Integer, comment="مرجوع آنلاین")
    branch_dissatisfaction = Column(Integer, comment="نارضایتی از شعبه")
    payment_followup = Column(Integer, comment="پیگیری واریزی")
    incomplete_delivery = Column(Integer, comment="ارسال ناقص")
    b2b_sales = Column(Integer, comment="فروش سازمانی")
    waiting_for_payment = Column(Integer, comment="در انتظار پرداخت")
    product_search = Column(Integer, comment="سرچ کالا")
    after_sales_service = Column(Integer, comment="خدمات پس از فروش")
    club = Column(Integer, comment="باشگاه")
    other = Column(Integer, comment="متفرقه")
    branch_info = Column(Integer, nullable=True, comment="اطلاعات شعب")
    product_site_info = Column(Integer, nullable=True, comment="اطلاعات سایت و محصول")
    snapp_pay = Column(Integer, nullable=True, comment="اسنپ‌پی")
    inner_call = Column(Integer, nullable=True, comment="داخلی")

    datetime = Column(Date)
    start_datetime = Column(DateTime, comment="اولین زمان تماس در روز")
    end_datetime = Column(DateTime, comment="آخرین زمان تماس در روز")