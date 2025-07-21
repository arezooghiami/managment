from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserLogin

def authenticate_user(db: Session, login_data: UserLogin):
    return db.query(User).filter(
        User.name == login_data.name,
        User.code == login_data.code
    ).first()

def get_all_users(db: Session):
    return db.query(User).all()

def create_user(db: Session, user_data):
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

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
