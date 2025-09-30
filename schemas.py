from pydantic import BaseModel
from typing import Optional

# ---------------- AUTH ----------------
class UserRegister(BaseModel):
    contact: str
    fullname: str
    password: str
    role: str = "student"

    def validate_role(self):
        if self.role not in ["student", "teacher"]:
            raise ValueError("Role must be 'student' or 'teacher'")


class UserLogin(BaseModel):
    contact: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int

# ---------------- STUDENTS ----------------
class StudentCreate(BaseModel):
    student_number: str
    name: str
    email: Optional[str] = None
    age: int
    grade: Optional[float] = None

class StudentOut(BaseModel):
    id: int
    student_number: str
    name: str
    email: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[float] = None
    account_id: Optional[int]

    model_config = {"from_attributes": True}

# ---------------- EXAMS ----------------
class ExamCreate(BaseModel):
    title: str
    total_marks: int

class ExamOut(BaseModel):
    id: int
    title: str
    total_marks: int
    model_config = {"from_attributes": True}

# ---------------- RESULTS ----------------
class ResultCreate(BaseModel):
    student_id: int
    exam_id: int
    score: float

class ResultOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    exam_id: int
    exam_title: str
    score: float
    model_config = {"from_attributes": True}
