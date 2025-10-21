from fastapi import FastAPI, Depends, HTTPException, Form
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from email.message import EmailMessage
import smtplib
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging
import models
import database
from database import get_db, init_db
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, IntegrityError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# ENVIRONMENT = os.getenv("ENVIRONMENT", "local")

# if ENVIRONMENT == "production":
#     allowed_origins = [os.getenv("CORS_ORIGINS_PROD")]
# else:
#     # allowed_origins = [os.getenv("CORS_ORIGINS_LOCAL")]
#     allowed_origins = "*"
    
# logger.info(f"Allowed Origins: {allowed_origins}")

origins = [
    "https://your-frontend-domain.com",  # e.g., your Render web app
    "http://localhost:5173",             # for local testing if you use Vite
]

# Lifespan event to initialize DB on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        init_db()  # Create tables using direct connection
        logger.info("✓ Application started")
    except Exception as e:
        logger.warning(f"⚠ Startup warning: {e}")
    
    yield
    
    # Shutdown
    logger.info("✓ Application shutdown")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    username: str
    password: str


@app.exception_handler(OperationalError)
async def db_connection_error_handler(request, exc):
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database connection failed. Please try again later."},
    )

@app.get("/")
def root():
    return {"message": "API is running"}


def create_user(db: Session, user: UserCreate):
    new_user = models.User(
        username=user.username,
        password=user.password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_user_count(db: Session):
    return db.query(models.User).count()


def send_email_notification(total_count: int):
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT"))
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_TO = os.getenv("EMAIL_TO")

    msg = EmailMessage()
    msg["Subject"] = "New Users Signup Notification"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg.set_content(f"There are now {total_count} registered users.")

    try:
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        logger.info("✓ Email notification sent")
    except Exception as e:
        logger.error(f"✗ Email failed: {e}")


@app.post("/login/")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Login attempt - Username: {user.username}")
    new_user = create_user(db, user)
    total = get_user_count(db)

    if total % 10 == 0:
        send_email_notification(total)

    return {"message": "User registered successfully", "user": new_user, "total_users": total}

\
@app.get("/users/")
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}, 503