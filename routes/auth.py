# auth.py
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt

from database import get_db
from models import Account, Student
from schemas import UserRegister, UserLogin, Token

# ---------------- SETTINGS ----------------
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------- HELPERS ----------------
def hash_password(password: str) -> str:
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ---------------- ROUTES ----------------
@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    Self-registration: students or teachers can register.
    Admin role is NOT allowed here.
    """
    # Validate role
    try:
        data.validate_role()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if contact/email already exists
    if db.query(Account).filter(Account.contact == data.contact).first():
        raise HTTPException(status_code=400, detail="Contact already registered")

    # Create account
    account = Account(
        contact=data.contact,
        fullname=data.fullname.strip(),
        password_hash=hash_password(data.password),
        role=data.role,  # now uses the role from input
        created_at=datetime.utcnow()
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    # If role is student, create linked Student record
    if data.role == "student":
        student = Student(
            student_number=account.contact,
            name=account.fullname,
            email=account.contact,
            created_at=datetime.utcnow(),
            account_id=account.id
        )
        db.add(student)
        db.commit()

    # Generate JWT for immediate login
    token = create_access_token({
        "sub": account.contact,
        "user_id": account.id,
        "role": account.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": account.role,
        "user_id": account.id
    }


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Login with contact and password."""
    if not data.contact or not data.password:
        raise HTTPException(status_code=400, detail="Contact and password are required")

    account = db.query(Account).filter(Account.contact == data.contact).first()
    if not account or not verify_password(data.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": account.contact,
        "user_id": account.id,
        "role": account.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": account.role,
        "user_id": account.id
    }
