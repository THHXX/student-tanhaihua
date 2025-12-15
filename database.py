import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL is None:
    print("未找到云数据库环境变量，正在使用本地数据库...")
    DATABASE_URL = "postgresql+psycopg2://user:password@localhost/student_db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(50), nullable=False)
    student_no = Column(String(50), nullable=False)
    class_name = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_key = Column(String(255))
    file_url = Column(String(512))
    storage_provider = Column(String(50))
    content_type = Column(String(100))
    file_size = Column(Integer)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
