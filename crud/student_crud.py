from sqlalchemy.orm import Session
from database import Student
from sqlalchemy import or_
from schemas import StudentCreate, StudentUpdate


def get_students(db: Session, skip: int = 0, limit: int = 100):
    q = db.query(Student)
    q = q.filter((Student.name != "") & (or_(Student.class_name == None, Student.class_name != "")))
    return q.offset(skip).limit(limit).all()


def get_student(db: Session, student_id: int):
    return db.query(Student).filter(Student.id == student_id).first()


def create_student(db: Session, student: StudentCreate):
    obj = Student(**student.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_student(db: Session, student_id: int, student: StudentUpdate):
    obj = get_student(db, student_id)
    if not obj:
        return None
    data = student.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_student(db: Session, student_id: int):
    obj = get_student(db, student_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return obj