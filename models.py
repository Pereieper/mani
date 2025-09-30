from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    contact = Column(String(50), unique=True, index=True)
    fullname = Column(String(150), nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), default="student")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    student = relationship("Student", back_populates="account", uselist=False)

class Student(Base):
    __tablename__ = "studentspelec"
    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(50), unique=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    grade = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    account_id = Column(Integer, ForeignKey("accounts.id"), unique=True, nullable=True)
    account = relationship("Account", back_populates="student")

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    total_marks = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("studentspelec.id"))
    exam_id = Column(Integer, ForeignKey("exams.id"))
    score = Column(Float, nullable=False)
    taken_at = Column(TIMESTAMP, default=datetime.utcnow)
    student = relationship("Student")
    exam = relationship("Exam")
