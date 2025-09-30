from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import Student
from schemas import StudentOut, StudentCreate
from auth import verify_token  # your JWT verification

router = APIRouter(prefix="/students", tags=["Students"])

# GET all students (admin/teacher) or only self (student)
@router.get("/", response_model=List[StudentOut])
def get_students(user=Depends(verify_token), db: Session = Depends(get_db)):
    if user["role"] == "student":
        student = db.query(Student).filter(Student.account_id == user["user_id"]).first()
        return [student] if student else []
    return db.query(Student).all()

# ADD student (admin only)
@router.post("/", response_model=StudentOut)
def add_student(student: StudentCreate, user=Depends(verify_token), db: Session = Depends(get_db)):
    if user["role"] != "admin":
        raise HTTPException(403, "Only admin can add students")
    
    new_student = Student(
        student_number=student.student_number,
        name=student.name,
        email=student.email,
        age=student.age,
        grade=student.grade,
        created_at=datetime.utcnow(),
        account_id=None  # admin-added, not linked to user account
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student
