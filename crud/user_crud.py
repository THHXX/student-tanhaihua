from sqlalchemy.orm import Session
from database import User
from schemas import UserCreate


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user: UserCreate, password_hash: str):
    obj = User(username=user.username, hashed_password=password_hash)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj