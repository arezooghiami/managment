from datetime import date
from enum import Enum
from pydantic import BaseModel



class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserBase(BaseModel):
    name: str
    family: str
    code: str
    role: UserRole


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    name: str
    code: str
