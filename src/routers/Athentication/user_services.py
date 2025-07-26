from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserLogin, UserRole


def authenticate_user(db: Session, login_data: UserLogin):
    return db.query(User).filter(
        User.name == login_data.name,
        User.code == login_data.code
    ).first()

def get_all_users(db: Session):
    return db.query(User).all()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(db, user_data):
    hashed_password = pwd_context.hash(user_data["password"])
    new_user = User(
        name=user_data["name"],
        family=user_data["family"],
        code=user_data["code"],
        password=hashed_password,
        role=UserRole(user_data["role"]),
        office_id=user_data["office_id"]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def delete_user(db: Session, user_id: int):
    user = db.query(User).get(user_id)
    if user:
        db.delete(user)
        db.commit()
    return user

def update_user(db: Session, user_id: int, updated_data):
    user = db.query(User).get(user_id)
    if not user:
        return None
    for field, value in updated_data.dict().items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
