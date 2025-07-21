# schemas/lunch.py

from pydantic import BaseModel
from datetime import date

class LunchCreate(BaseModel):
    title: str
    description: str | None = None
    date: date

class LunchRead(BaseModel):
    id: int
    title: str
    description: str | None = None
    date: date

    class Config:
        orm_mode = True
from pydantic import BaseModel
from datetime import date
from typing import Optional

class LunchMenuBase(BaseModel):
    week_start_date: date
    menu_details: str

class LunchMenuCreate(LunchMenuBase):
    pass

class LunchMenu(LunchMenuBase):
    id: int
    created_by: str

    class Config:
        orm_mode = True

class LunchOrderBase(BaseModel):
    order_date: date
    food_item: str

class LunchOrderCreate(LunchOrderBase):
    pass

class LunchOrder(LunchOrderBase):
    id: int
    user_code: str
    menu_id: int

    class Config:
        orm_mode = True