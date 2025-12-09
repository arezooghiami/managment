from sqlalchemy import Column, Integer, String

from DB.database import Base


class ComplaintIssue(Base):
    __tablename__ = 'complaint_issues'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, comment="عنوان شکایت از پیش تعریف شده")
