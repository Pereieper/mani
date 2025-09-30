import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 1️⃣ Load .env
load_dotenv()  # mangita sa .env sa same folder

# 2️⃣ Kuha ang DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found. Check your .env file!")

print("DATABASE_URL loaded successfully!")

# 3️⃣ Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# 4️⃣ Test connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()
        print("Connected to PostgreSQL version:", version[0])
except Exception as e:
    print("Error connecting to database:", e)
