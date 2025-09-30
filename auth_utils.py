# auth_utils.py
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
from models import Account

# ---------------- ENV / SETTINGS ----------------
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# ---------------- Password Hashing ----------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ---------------- JWT TOKEN ----------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(user_id: int, contact: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token including user_id, contact, and role.
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": contact,
        "user_id": user_id,
        "role": role,
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_account(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Account:
    """
    Verify JWT token and return current Account object.
    Raises 401 if invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        contact: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        if not all([contact, user_id, role]):
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    account = db.query(Account).filter(Account.id == user_id, Account.contact == contact).first()
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")
    
    return account
