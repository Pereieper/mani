import os
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, joinedload
from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext

from database import Base, get_db
from models import Account, Student, Exam, Result
from schemas import StudentCreate, StudentOut, ExamCreate, ExamOut, ResultCreate, ResultOut
from routes.auth import router as auth_router

# ---------------- ENV ----------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env")

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# ---------------- DB ----------------
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# ---------------- APP ----------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
security = HTTPBearer()
app = FastAPI(title="Online Exam Management API")
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

# ---------------- JWT HELPERS ----------------
def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_account(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> Account:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    account = db.query(Account).filter(Account.id == user_id).first()
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")
    return account

# ---------------- DEPENDENCY ----------------
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- SEED ADMIN ----------------
@app.on_event("startup")
def seed_admin():
    db = SessionLocal()
    admin_contact = os.getenv("ADMIN_CONTACT", "admin@example.com")
    admin_name = os.getenv("ADMIN_NAME", "Administrator")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    if not db.query(Account).filter(Account.contact == admin_contact).first():
        account = Account(
            contact=admin_contact,
            fullname=admin_name,
            password_hash=pwd_context.hash(admin_password),
            role="admin"
        )
        db.add(account)
        db.commit()
        print(f"Seeded admin: {admin_contact} / {admin_password}")
    db.close()

# ---------------- STUDENTS ----------------
@app.get("/students", response_model=List[StudentOut])
def get_students(current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    if current_user.role == "student":
        student = db.query(Student).filter(Student.account_id == current_user.id).first()
        return [student] if student else []
    # Admin and teacher can see all students
    return db.query(Student).all()

@app.post("/students", response_model=StudentOut)
def add_student(student: StudentCreate, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="No permission")
    account = db.query(Account).filter(Account.contact == student.email).first()
    if not account:
        raise HTTPException(status_code=400, detail=f"No account found for {student.email}. Please create the account first.")
    new_student = Student(
        student_number=student.student_number,
        name=student.name,
        email=student.email,
        age=student.age,
        grade=student.grade,
        created_at=datetime.utcnow(),
        account_id=account.id
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@app.put("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, student: StudentCreate, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    for k, v in student.dict().items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s

@app.delete("/students/{student_id}")
def delete_student(student_id: int, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(404, "Student not found")
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    db.delete(s)
    db.commit()
    return {"message": "Student deleted"}

# ---------------- EXAMS ----------------
@app.get("/exams", response_model=List[ExamOut])
def get_exams(current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    return db.query(Exam).all()

@app.post("/exams", response_model=ExamOut)
def add_exam(exam: ExamCreate, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    new_exam = Exam(**exam.dict())
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    return new_exam

@app.put("/exams/{exam_id}", response_model=ExamOut)
def update_exam(exam_id: int, exam: ExamCreate, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    e = db.query(Exam).filter(Exam.id == exam_id).first()
    if not e:
        raise HTTPException(404, "Exam not found")
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    for k, v in exam.dict().items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return e

@app.delete("/exams/{exam_id}")
def delete_exam(exam_id: int, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    e = db.query(Exam).filter(Exam.id == exam_id).first()
    if not e:
        raise HTTPException(404, "Exam not found")
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    db.delete(e)
    db.commit()
    return {"message": "Exam deleted"}

# ---------------- RESULTS ----------------
@app.get("/results", response_model=List[ResultOut])
def get_results(current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    # Start with base query for Results, with student and exam relationships loaded
    query = db.query(Result).options(joinedload(Result.student), joinedload(Result.exam))
    
    # If current user is a student, only fetch their results
    if current_user.role == "student":
        student = db.query(Student).filter(Student.account_id == current_user.id).first()
        if not student:
            return []  # No student record found for this account
        query = query.filter(Result.student_id == student.id)
    
    # Execute query
    results = query.all()
    
    # Transform results into the Pydantic schema
    return [
        ResultOut(
            id=r.id,
            student_id=r.student_id,
            student_name=r.student.name if r.student else "Unknown",
            exam_id=r.exam_id,
            exam_title=r.exam.title if r.exam else "Unknown",
            score=r.score
        )
        for r in results
    ]


@app.post("/results", response_model=ResultOut)
def add_result(result: ResultCreate = Body(...), current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    student = db.query(Student).filter(Student.id == result.student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    exam = db.query(Exam).filter(Exam.id == result.exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    new_result = Result(
        student_id=student.id,
        exam_id=exam.id,
        score=result.score,
        taken_at=datetime.utcnow()
    )
    db.add(new_result)
    db.commit()
    db.refresh(new_result)
    return ResultOut(
        id=new_result.id,
        student_id=new_result.student_id,
        student_name=new_result.student.name,
        exam_id=new_result.exam_id,
        exam_title=new_result.exam.title,
        score=new_result.score
    )

@app.put("/results/{result_id}", response_model=ResultOut)
def update_result(result_id: int, result: ResultCreate = Body(...), current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    r = db.query(Result).filter(Result.id == result_id).first()
    if not r:
        raise HTTPException(404, "Result not found")
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    student = db.query(Student).filter(Student.id == result.student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")
    exam = db.query(Exam).filter(Exam.id == result.exam_id).first()
    if not exam:
        raise HTTPException(404, "Exam not found")
    r.student_id = student.id
    r.exam_id = exam.id
    r.score = result.score
    db.commit()
    db.refresh(r)
    db.refresh(r.student)
    db.refresh(r.exam)
    return ResultOut(
        id=r.id,
        student_id=r.student_id,
        student_name=r.student.name,
        exam_id=r.exam_id,
        exam_title=r.exam.title,
        score=r.score
    )

@app.delete("/results/{result_id}")
def delete_result(result_id: int, current_user: Account = Depends(get_current_account), db: Session = Depends(get_db_session)):
    r = db.query(Result).filter(Result.id == result_id).first()
    if not r:
        raise HTTPException(404, "Result not found")
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(403, "No permission")
    db.delete(r)
    db.commit()
    return {"message": "Result deleted"}
