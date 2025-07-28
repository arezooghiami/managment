from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class Status(str, Enum):
    ACTIVE = "active"
    DEACTIVE = "deactive"


class UserBase(BaseModel):
    name: str
    family: str
    code: str
    password: str
    role: UserRole


class UserLogin(BaseModel):
    password: str
    code: str
