from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, BackgroundTasks, File, UploadFile
print("Starting LearnHub Backend...")
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import tempfile

import logging
from pathlib import Path
from dotenv import load_dotenv
import bcrypt
import dns.resolver

# Fix for MongoDB Atlas DNS resolution timeouts
# Forces the use of reliable public DNS servers
try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
except Exception as e:
    print(f"Warning: Could not configure custom DNS resolver: {e}")

# Load environment variables IMMEDIATELY
load_dotenv()
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail  
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import io
import stripe
import newsletter  # Newsletter module for weekly emails
# Bcrypt compatibility patch for passlib
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type('About', (object,), {'__version__': bcrypt.__version__})

# Set Stripe key
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

ROOT_DIR = Path(__file__).parent

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'learnhub')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT Settings
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Commission
ADMIN_COMMISSION = float(os.environ.get('ADMIN_COMMISSION', 0.15))

# Create the main app
app = FastAPI(title="LearnHub API")

# Mount Uploads directory for static access
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

api_router = APIRouter(prefix="/api")


# ==================== MODELS ====================
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    role: str = "student"  # admin, instructor, student
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Instructor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    verification_status: str = "pending"  # pending, approved, rejected
    earnings: float = 0.0
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Course(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instructor_id: str
    title: str
    description: str
    category: str
    price: float
    discount_price: Optional[float] = None
    thumbnail: Optional[str] = None
    status: str = "draft"  # draft, published, archived, rejected
    video_platform: Optional[str] = "youtube"  # youtube, vimeo
    preview_video: Optional[str] = None
    difficulty_level: str = "Beginner"  # Beginner, Intermediate, Advanced
    language: str = "English"
    requirements: List[str] = []
    outcomes: List[str] = []
    faqs: List[Dict[str, str]] = []  # List of {"question": str, "answer": str}
    meta_keywords: Optional[str] = None
    meta_description: Optional[str] = None
    drip_content: bool = False
    is_featured: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Section(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    title: str
    description: Optional[str] = None
    order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Lesson(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    section_id: Optional[str] = None  # Can be in a section or standalone
    title: str
    type: str  # video, pdf, text, live_class
    content_url: Optional[str] = None
    content_text: Optional[str] = None
    notes_url: Optional[str] = None # Added for supplementary reading materials
    duration: Optional[int] = None  # in minutes
    order: int = 0
    is_preview: bool = False  # Can be previewed without enrollment
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LiveClass(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    section_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    duration: int  # in minutes
    meeting_url: Optional[str] = None
    status: str = "scheduled"  # scheduled, live, completed, cancelled
    max_attendees: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Enrollment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    progress: float = 0.0  # 0-100
    completed_lessons: List[str] = []  # List of completed lesson IDs
    status: str = "active"  # active, completed
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Quiz(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    title: str
    questions: List[Dict[str, Any]]  # [{question, options, correct_answer}]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuizResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    quiz_id: str
    course_id: str
    score: float
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Payment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    amount: float
    original_amount: Optional[float] = None
    discount_amount: Optional[float] = 0.0
    coupon_code: Optional[str] = None
    session_id: Optional[str] = None
    payment_status: str = "pending"  # pending, paid, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Coupon(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    discount_type: str  # percentage, fixed
    discount_value: float
    valid_from: datetime
    valid_until: datetime
    usage_limit: Optional[int] = None  # None = unlimited
    used_count: int = 0
    is_active: bool = True
    applicable_courses: Optional[List[str]] = None  # None = all courses
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CouponUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    coupon_id: str
    user_id: str
    course_id: str
    discount_amount: float
    used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Certificate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    issued_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BlogPost(BaseModel):
    """Blog posts for weekly newsletter"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    slug: str  # URL-friendly: "why-python-is-perfect"
    content: str  # Markdown content
    excerpt: str  # Short summary
    cover_image: Optional[str] = None
    course_id: Optional[str] = None  # Related course
    author_id: str
    category: str = "Newsletter"
    status: str = "published"
    views: int = 0
    sent_to_subscribers: bool = False
    email_sent_count: int = 0
    published_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmailSubscription(BaseModel):
    """Newsletter email subscriptions"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None  # For registered users
    email: EmailStr
    subscribed: bool = True
    unsubscribe_token: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subscription_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    course_id: str
    rating: int  # 1-5 stars
    review_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ==================== UTILITIES ====================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def send_reset_email(email: str, token: str):
    print(f"DEBUG: Entering send_reset_email for {email}")
    try:
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_url}/reset-password?token={token}"
        
        # CLEARLY PRINT THE LINK TO THE CONSOLE FOR THE USER
        print("\n" + "="*50)
        print(f"PASSWORD RESET LINK FOR: {email}")
        print(reset_link)
        print("="*50 + "\n")
        
        logger.info(f"Password Reset Link generated: {reset_link}")

        api_key = os.environ.get('SENDGRID_API_KEY')
        sender = os.environ.get('SENDER_EMAIL')
        
        print(f"DEBUG: SendGrid API Key exists: {bool(api_key)}")
        print(f"DEBUG: Sender Email: {sender}")

        if not api_key:
            logger.warning("SendGrid API Key (SENDGRID_API_KEY) is missing from environment variables. Skipping email send.")
            return

        if not sender:
            logger.warning("Sender Email (SENDER_EMAIL) is missing from environment variables. Skipping email send.")
            return

        message = Mail(
            from_email=sender,
            to_emails=email,
            subject='Reset Your LearnHub Password',
            html_content=f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
                    <h1 style="color: #1e40af; font-size: 24px;">Reset Your Password</h1>
                    <p style="color: #374151; line-height: 1.5;">You requested to reset your password for LearnHub. Click the button below to set a new password. This link is valid for 1 hour.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password</a>
                    </div>
                    <p style="color: #6b7280; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>
                </div>
            """
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        print(f"DEBUG: SendGrid Response Status Code: {response.status_code}")
        print(f"DEBUG: SendGrid Response Body: {response.body}")
        logger.info(f"Password reset email sent to {email}. Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send reset email: {str(e)}")
        print(f"DEBUG: SendGrid ERROR: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user_doc:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user_doc)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_optional_user(request: Request):
    try:
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        
        if not token:
            token = request.query_params.get("token")
            
        if not token:
            return None
            
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
        if not user_doc:
            return None
        return User(**user_doc)
    except Exception:
        return None


async def check_enrollment_status(user_id: str, course_id: str) -> bool:
    enrollment = await db.enrollments.find_one({
        "user_id": user_id, 
        "course_id": course_id,
        "status": {"$in": ["active", "completed"]}
    })
    return enrollment is not None


async def send_email(to: str, subject: str, content: str):
    try:
        message = Mail(
            from_email=os.getenv('SENDER_EMAIL'),
            to_emails=to,
            subject=subject,
            html_content=content
        )
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        logging.error(f"Email sending failed: {str(e)}")


# ==================== AUTH ROUTES ====================
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump()
    password = user_dict.pop("password")
    hashed_pw = hash_password(password)
    
    user = User(**user_dict)
    
    # Force role to student for new signups (even if they requested instructor)
    # They will be promoted after approval
    requested_role = user.role
    user.role = "student"
    
    user_doc = user.model_dump()
    user_doc['password'] = hashed_pw
    user_doc['role'] = "student"
    user_doc['created_at'] = user_doc['created_at'].isoformat()
    
    await db.users.insert_one(user_doc)
    
    # AUTO-CREATE INSTRUCTOR DOCUMENT if user registers as instructor
    if requested_role == "instructor":
        instructor = Instructor(
            user_id=user.id,
            verification_status="pending",
            bio="Instructor registration"
        )
        instructor_doc = instructor.model_dump()
        instructor_doc['created_at'] = instructor_doc['created_at'].isoformat()
        await db.instructors.insert_one(instructor_doc)
        logger.info(f"Created pending instructor profile for user {user.id}")
    
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"token": token, "user": user}


@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc or not verify_password(credentials.password, user_doc.get('password', '')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'password'})
    
    # Repair missing ID if needed
    if "id" not in user_doc:
        user_id = str(uuid.uuid4())
        await db.users.update_one({"email": credentials.email}, {"$set": {"id": user_id}})
        user.id = user_id
        logger.info(f"Fixed missing ID for user {user.email}: {user_id}")
    else:
        user.id = user_doc['id']
        
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"token": token, "user": user}


@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    print(f"DEBUG: Forgot Password requested for: {data.email}")
    user_doc = await db.users.find_one({"email": data.email})
    
    if not user_doc:
        print(f"DEBUG: User NOT found in database: {data.email}")
        return {"message": "If an account exists with this email, a reset link has been sent."}
    
    print(f"DEBUG: User found: {user_doc.get('id')} - {user_doc.get('email')}")
    
    # Create a short-lived reset token (1 hour)
    reset_data = {"sub": user_doc["id"], "type": "reset"}
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    reset_data.update({"exp": expire})
    
    try:
        reset_token = jwt.encode(reset_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        print("DEBUG: Reset token generated successfully")
    except Exception as e:
        print(f"DEBUG: TOKEN GENERATION FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail="Token generation failed")
    
    background_tasks.add_task(send_reset_email, data.email, reset_token)
    print("DEBUG: Background task 'send_reset_email' scheduled")
    
    return {"message": "If an account exists with this email, a reset link has been sent."}


@api_router.post("/auth/reset-password")
async def reset_password(data: ResetPasswordRequest):
    try:
        payload = jwt.decode(data.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")
            
        hashed_pw = hash_password(data.new_password)
        await db.users.update_one({"id": user_id}, {"$set": {"password": hashed_pw}})
        
        return {"message": "Password reset successfully. You can now log in."}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")


@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@api_router.patch("/users/profile")
async def update_profile(updates: dict, current_user: User = Depends(get_current_user)):
    allowed_fields = ["name", "bio", "profile_image"]
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    await db.users.update_one({"id": current_user.id}, {"$set": update_data})
    
    # Sync bio with instructor profile if it exists
    if "bio" in update_data:
        await db.instructors.update_one({"user_id": current_user.id}, {"$set": {"bio": update_data["bio"]}})
    
    return {"message": "Profile updated successfully"}


@api_router.patch("/users/profile/password")
async def update_password(data: PasswordUpdate, current_user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user.id})
    if not user_doc or not verify_password(data.old_password, user_doc.get('password', '')):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    hashed_pw = hash_password(data.new_password)
    await db.users.update_one({"id": current_user.id}, {"$set": {"password": hashed_pw}})
    
    return {"message": "Password updated successfully"}


@api_router.get("/users/profile/{user_id}")
async def get_public_profile(user_id: str):
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user_doc:
        logger.error(f"Public Profile lookup failed: User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    # Also fetch courses taught by this user if they are an instructor
    courses = []
    if user_doc.get('role') in ['instructor', 'admin']:
        instructor = await db.instructors.find_one({"user_id": user_id})
        if instructor:
            courses = await db.courses.find({"instructor_id": instructor['id'], "status": "published"}, {"_id": 0}).to_list(100)
        elif user_doc.get('role') == 'admin':
            # Handle admin as instructor case if needed
            courses = await db.courses.find({"status": "published"}, {"_id": 0}).to_list(10) # Just some courses for admin

    return {**user_doc, "courses": courses}


# ==================== INSTRUCTOR ROUTES ====================
@api_router.post("/instructors/apply")
async def apply_instructor(bio: str, current_user: User = Depends(get_current_user)):
    existing = await db.instructors.find_one({"user_id": current_user.id})
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")
    
    instructor = Instructor(user_id=current_user.id, bio=bio, verification_status="pending")
    doc = instructor.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.instructors.insert_one(doc)
    
    # role remains student until admin approves
    
    return {"message": "Instructor application submitted and pending approval", "instructor": instructor}


@api_router.get("/instructors")
async def get_instructors(status: Optional[str] = None):
    query = {}
    if status:
        query['verification_status'] = status
    instructors = await db.instructors.find(query, {"_id": 0}).to_list(1000)
    
    # Ensure all instructors have stable IDs
    return instructors


@api_router.patch("/instructors/{instructor_id}/approve")
async def approve_instructor(instructor_id: str, approved: bool, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_status = "approved" if approved else "rejected"
    result = await db.instructors.update_one(
        {"id": instructor_id},
        {"$set": {"verification_status": new_status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Instructor not found")
        
    # Promote user to instructor role if approved
    if approved:
        instructor = await db.instructors.find_one({"id": instructor_id})
        if instructor:
            await db.users.update_one({"id": instructor['user_id']}, {"$set": {"role": "instructor"}})
            logger.info(f"Promoted user {instructor['user_id']} to instructor")
    
    return {"message": f"Instructor {new_status}"}


# ==================== COURSE ROUTES ====================
@api_router.post("/courses", response_model=Course)
async def create_course(course_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Only instructors and admins can create courses")
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor:
        # Create a stable instructor profile if missing
        instructor_id = str(uuid.uuid4())
        new_instructor = {
            "id": instructor_id,
            "user_id": current_user.id,
            "verification_status": "approved",
            "earnings": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.instructors.insert_one(new_instructor)
        logger.info(f"Auto-created instructor profile for {current_user.email}")
    else:
        instructor_id = instructor['id']
        if not instructor_id:
            instructor_id = str(uuid.uuid4())
            await db.instructors.update_one({"user_id": current_user.id}, {"$set": {"id": instructor_id}})
            logger.info(f"Repaired missing instructor ID for {current_user.email}")
    
    try:
        course = Course(instructor_id=instructor_id, **course_data)
        # Force status to pending for moderation
        course.status = "pending"
        
        doc = course.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.courses.insert_one(doc)
        return course
    except Exception as e:
        logging.error(f"Course creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error during course creation: {str(e)}")


# ==================== ADMIN COURSE ROUTES ====================
@api_router.get("/admin/courses/pending")
async def get_pending_courses(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    courses = await db.courses.find({"status": "pending"}, {"_id": 0}).to_list(100)
    
    # Enrich with instructor name
    for course in courses:
        instructor = await db.instructors.find_one({"id": course['instructor_id']})
        if instructor:
            user = await db.users.find_one({"id": instructor['user_id']})
            course['instructor_name'] = user['name'] if user else "Unknown"
            
    return courses

@api_router.patch("/admin/courses/{course_id}/moderate")
async def moderate_course(course_id: str, approved: bool, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    new_status = "published" if approved else "rejected"
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"status": new_status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
        
    return {"message": f"Course {new_status}"}

@api_router.patch("/admin/courses/{course_id}/feature")
async def feature_course(course_id: str, featured: bool, current_user: User = Depends(get_current_user)):
     if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
     result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"is_featured": featured}}
    )
     if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
        
     return {"message": f"Course featured status updated"}


@api_router.get("/courses")
async def get_courses(
    request: Request,
    category: Optional[str] = None,
    status: Optional[str] = "published",
    search: Optional[str] = None,
    instructor_id: Optional[str] = None,
    token: Optional[str] = None
):
    current_user = await get_optional_user(request)
    if not current_user and token:
        # Fallback for explicit token param if get_optional_user missed it
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
            if user_doc:
                current_user = User(**user_doc)
        except:
            pass

    query = {}
    if category:
        query['category'] = category
        
    # Security: Only admins or owners can see non-published courses
    if status == 'all' or status == 'draft':
        if not current_user:
            # Not logged in? Only see published
            query['status'] = "published"
        elif current_user.role == 'admin':
            # Admin sees everything
            pass
        else:
            # Instructor sees their own all/draft, but others only see published
            # We enforce their instructor_id if they aren't admin
            instructor = await db.instructors.find_one({"user_id": current_user.id})
            if instructor:
                query['instructor_id'] = instructor['id']
                if status != 'all':
                    query['status'] = status
            else:
                # Not an instructor? Only see published
                query['status'] = "published"
    else:
        query['status'] = status or "published"

    if instructor_id:
        query['instructor_id'] = instructor_id
    if search:
        query['$or'] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}}
        ]
    
    courses = await db.courses.find(query, {"_id": 0}).to_list(1000)
    return courses


@api_router.get("/courses/{course_id}")
async def get_course(course_id: str):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Get instructor info
    instructor = await db.instructors.find_one({"id": course['instructor_id']}, {"_id": 0})
    if instructor:
        user = await db.users.find_one({"id": instructor['user_id']}, {"_id": 0, "password": 0})
        course['instructor'] = user
    
    # Get lessons count
    lessons_count = await db.lessons.count_documents({"course_id": course_id})
    course['lessons_count'] = lessons_count
    
    return course


@api_router.patch("/courses/{course_id}")
async def update_course(course_id: str, updates: dict, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Allow Admin or Course Owner
    is_owner = False
    if current_user.role != "admin":
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_owner = True
        
        if not is_owner:
            raise HTTPException(status_code=403, detail="Not authorized to update this course")
    
    # Remove immutable fields from updates
    updates.pop('id', None)
    updates.pop('instructor_id', None)
    
    await db.courses.update_one({"id": course_id}, {"$set": updates})
    return {"message": "Course updated", "status": "published"}

@api_router.delete("/courses/{course_id}")
async def delete_course(course_id: str, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to delete this course")
        
    # Delete course and related data
    await db.courses.delete_one({"id": course_id})
    await db.sections.delete_many({"course_id": course_id})
    await db.lessons.delete_many({"course_id": course_id})
    await db.quizzes.delete_many({"course_id": course_id})
    await db.live_classes.delete_many({"course_id": course_id})
    # Note: Enrollments are usually kept for audit but could be archived
    
    return {"message": "Course and all related content deleted successfully"}


@api_router.post("/courses/{course_id}/lessons")
async def add_lesson(course_id: str, lesson_data: dict, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    lesson = Lesson(course_id=course_id, **lesson_data)
    doc = lesson.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.lessons.insert_one(doc)    
    
    # NEW: Reset completion status for all enrolled students
    # When a new lesson is added, completed courses should become "active" again
    await db.enrollments.update_many(
        {"course_id": course_id, "status": "completed"},
        {"$set": {"status": "active"}}
    )
    
    return lesson


@api_router.get("/courses/{course_id}/lessons")
async def get_lessons(course_id: str, request: Request):
    lessons = await db.lessons.find({"course_id": course_id}, {"_id": 0}).sort("order", 1).to_list(1000)
    
    current_user = await get_optional_user(request)
    is_authorized = False
    
    if current_user:
        if current_user.role == "admin":
            is_authorized = True
        else:
            course = await db.courses.find_one({"id": course_id})
            if course:
                instructor = await db.instructors.find_one({"user_id": current_user.id})
                if instructor and instructor['id'] == course.get('instructor_id'):
                    is_authorized = True
            
            if not is_authorized:
                is_authorized = await check_enrollment_status(current_user.id, course_id)
                
    # Filter content for non-enrolled users
    for lesson in lessons:
        if not is_authorized and not lesson.get('is_preview', False):
            lesson['content_url'] = None
            lesson['content_text'] = "Private content. Enroll to view."
            
    return lessons


@api_router.patch("/lessons/{lesson_id}")
async def update_lesson(lesson_id: str, updates: dict, current_user: User = Depends(get_current_user)):
    lesson = await db.lessons.find_one({"id": lesson_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    course = await db.courses.find_one({"id": lesson['course_id']})
    
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Remove immutable fields
    updates.pop('id', None)
    updates.pop('course_id', None)
    updates.pop('created_at', None)
    
    if not updates:
        return lesson
        
    await db.lessons.update_one({"id": lesson_id}, {"$set": updates})
    
    updated_lesson = await db.lessons.find_one({"id": lesson_id}, {"_id": 0})
    return updated_lesson


@api_router.delete("/lessons/{lesson_id}")
async def delete_lesson(lesson_id: str, current_user: User = Depends(get_current_user)):
    lesson = await db.lessons.find_one({"id": lesson_id})
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    course = await db.courses.find_one({"id": lesson['course_id']})
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.lessons.delete_one({"id": lesson_id})
    return {"message": "Lesson deleted"}


# ==================== SECTION ROUTES ====================
@api_router.post("/courses/{course_id}/sections")
async def create_section(course_id: str, section_data: dict, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    section = Section(course_id=course_id, **section_data)
    doc = section.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.sections.insert_one(doc)
    return section


@api_router.patch("/sections/{section_id}")
async def update_section(section_id: str, updates: dict, current_user: User = Depends(get_current_user)):
    section = await db.sections.find_one({"id": section_id})
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
        
    course = await db.courses.find_one({"id": section['course_id']})
    if not course:
        raise HTTPException(status_code=404, detail="Course associated with section not found")
        
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Remove immutable fields if present
    updates.pop('id', None)
    updates.pop('course_id', None)
    updates.pop('created_at', None)
    
    await db.sections.update_one({"id": section_id}, {"$set": updates})
    return {"message": "Section updated successfully"}



@api_router.get("/courses/{course_id}/sections")
async def get_sections(course_id: str, request: Request):
    sections = await db.sections.find({"course_id": course_id}, {"_id": 0}).sort("order", 1).to_list(1000)
    
    current_user = await get_optional_user(request)
    is_authorized = False
    
    if current_user:
        if current_user.role == "admin":
            is_authorized = True
        else:
            course = await db.courses.find_one({"id": course_id})
            if course:
                instructor = await db.instructors.find_one({"user_id": current_user.id})
                if instructor and instructor['id'] == course.get('instructor_id'):
                    is_authorized = True
            
            if not is_authorized:
                is_authorized = await check_enrollment_status(current_user.id, course_id)
    
    # Get lessons for each section
    for section in sections:
        lessons = await db.lessons.find({"section_id": section['id']}, {"_id": 0}).sort("order", 1).to_list(1000)
        # Filter content for non-enrolled users
        for lesson in lessons:
            if not is_authorized and not lesson.get('is_preview', False):
                lesson['content_url'] = None
                lesson['content_text'] = "Private content. Enroll to view."
                if lesson.get('type') == 'video':
                    lesson['duration'] = 0 # Hide duration if preferred
        section['lessons'] = lessons
    
    return sections


@api_router.delete("/sections/{section_id}")
async def delete_section(section_id: str, current_user: User = Depends(get_current_user)):
    section = await db.sections.find_one({"id": section_id})
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    course = await db.courses.find_one({"id": section['course_id']})
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete section and its lessons
    await db.sections.delete_one({"id": section_id})
    await db.lessons.delete_many({"section_id": section_id})
    
    return {"message": "Section deleted"}


# ==================== LIVE CLASS ROUTES ====================
@api_router.post("/courses/{course_id}/live-classes")
async def create_live_class(course_id: str, live_class_data: dict, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Parse datetime
    scheduled_at = datetime.fromisoformat(live_class_data['scheduled_at'])
    
    live_class = LiveClass(
        course_id=course_id,
        section_id=live_class_data.get('section_id'),
        title=live_class_data['title'],
        description=live_class_data.get('description'),
        scheduled_at=scheduled_at,
        duration=int(live_class_data['duration']),
        meeting_url=live_class_data.get('meeting_url'),
        max_attendees=live_class_data.get('max_attendees')
    )
    
    doc = live_class.model_dump()
    doc['scheduled_at'] = doc['scheduled_at'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.live_classes.insert_one(doc)
    
    return live_class


@api_router.get("/courses/{course_id}/live-classes")
async def get_live_classes(course_id: str, request: Request):
    current_user = await get_optional_user(request)
    is_authorized = False
    
    if current_user:
        if current_user.role == "admin":
            is_authorized = True
        else:
            course = await db.courses.find_one({"id": course_id})
            if course:
                instructor = await db.instructors.find_one({"user_id": current_user.id})
                if instructor and instructor['id'] == course.get('instructor_id'):
                    is_authorized = True
            
            if not is_authorized:
                is_authorized = await check_enrollment_status(current_user.id, course_id)
                
    live_classes = await db.live_classes.find({"course_id": course_id}, {"_id": 0}).sort("scheduled_at", 1).to_list(1000)
    
    # Hide meeting URLs for non-enrolled users
    if not is_authorized:
        for lc in live_classes:
            lc['meeting_url'] = None
            lc['description'] = "Enroll to access the meeting link and details."
            
    return live_classes


@api_router.patch("/live-classes/{live_class_id}")
async def update_live_class(live_class_id: str, updates: dict, current_user: User = Depends(get_current_user)):
    live_class = await db.live_classes.find_one({"id": live_class_id})
    if not live_class:
        raise HTTPException(status_code=404, detail="Live class not found")
    
    course = await db.courses.find_one({"id": live_class['course_id']})
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.live_classes.update_one({"id": live_class_id}, {"$set": updates})
    return {"message": "Live class updated"}


@api_router.delete("/live-classes/{live_class_id}")
async def delete_live_class(live_class_id: str, current_user: User = Depends(get_current_user)):
    live_class = await db.live_classes.find_one({"id": live_class_id})
    if not live_class:
        raise HTTPException(status_code=404, detail="Live class not found")
    
    course = await db.courses.find_one({"id": live_class['course_id']})
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.live_classes.delete_one({"id": live_class_id})
    return {"message": "Live class deleted"}


# ==================== ENROLLMENT ROUTES ====================
@api_router.post("/enrollments")
async def create_enrollment(course_id: str, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    existing = await db.enrollments.find_one({"user_id": current_user.id, "course_id": course_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
    # Only allow direct enrollment if course is free
    if course.get('price', 0) > 0:
        raise HTTPException(status_code=400, detail="Premium course. Please purchase to enroll.")
        
    enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
    doc = enrollment.model_dump()
    doc['enrolled_at'] = doc['enrolled_at'].isoformat()
    await db.enrollments.insert_one(doc)
    return enrollment


@api_router.get("/enrollments/my-courses")
async def get_my_courses(current_user: User = Depends(get_current_user)):
    enrollments = await db.enrollments.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    result = []
    for enrollment in enrollments:
        course = await db.courses.find_one({"id": enrollment['course_id']}, {"_id": 0})
        if course:
            # Recalculate progress based on actual completed lessons
            completed_lessons = enrollment.get('completed_lessons', [])
            total_lessons = await db.lessons.count_documents({"course_id": enrollment['course_id']})
            
            if total_lessons > 0:
                actual_progress = (len(completed_lessons) / total_lessons) * 100
            else:
                actual_progress = 0
            
            # Update if progress doesn't match
            stored_progress = enrollment.get('progress', 0)
            if abs(actual_progress - stored_progress) > 1:
                new_status = 'completed' if actual_progress >= 100 else 'active'
                await db.enrollments.update_one(
                    {"id": enrollment['id']},
                    {"$set": {"progress": actual_progress, "status": new_status}}
                )
                enrollment['progress'] = actual_progress
                enrollment['status'] = new_status
            
            result.append({**enrollment, "course": course})
    
    return result



@api_router.patch("/enrollments/{enrollment_id}/progress")
async def update_progress(enrollment_id: str, progress: float, completed_lessons: Optional[str] = None, current_user: User = Depends(get_current_user)):
    enrollment = await db.enrollments.find_one({"id": enrollment_id, "user_id": current_user.id})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    updates = {"progress": progress}
    
    # If completed_lessons is provided (as JSON string), parse and update it
    parsed_lessons = None
    if completed_lessons is not None:
        try:
            parsed_lessons = json.loads(completed_lessons)
            updates["completed_lessons"] = parsed_lessons
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON
    
    cert_id = None
    
    if progress >= 100:
        updates['status'] = 'completed'
        # Try to generate certificate (will check quiz requirements)
        cert_id = await generate_certificate_if_eligible(current_user.id, enrollment['course_id'])
    else:
        updates['status'] = 'active'
    
    await db.enrollments.update_one({"id": enrollment_id}, {"$set": updates})
    
    return {
        "message": "Progress updated",
        "progress": progress,
        "completed_lessons": parsed_lessons or enrollment.get('completed_lessons', []),
        "certificate_earned": cert_id is not None,
        "certificate_id": cert_id
    }



@api_router.post("/enrollments/{enrollment_id}/complete-lesson")
async def complete_lesson(enrollment_id: str, lesson_id: str, current_user: User = Depends(get_current_user)):
    """Mark a lesson as complete and recalculate progress"""
    enrollment = await db.enrollments.find_one({"id": enrollment_id, "user_id": current_user.id})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Get current completed lessons
    completed_lessons = enrollment.get('completed_lessons', [])
    
    # Add lesson if not already completed
    if lesson_id not in completed_lessons:
        completed_lessons.append(lesson_id)
    
    # Get total lessons for this course
    total_lessons = await db.lessons.count_documents({"course_id": enrollment['course_id']})
    
    # Calculate progress
    if total_lessons > 0:
        progress = (len(completed_lessons) / total_lessons) * 100
    else:
        progress = 0
    
    progress = min(100, progress)  # Cap at 100%
    
    updates = {
        "completed_lessons": completed_lessons,
        "progress": progress
    }
    
    cert_id = None
    
    if progress >= 100:
        updates['status'] = 'completed'
        cert_id = await generate_certificate_if_eligible(current_user.id, enrollment['course_id'])
    
    await db.enrollments.update_one({"id": enrollment_id}, {"$set": updates})
    
    return {
        "message": "Lesson completed",
        "lesson_id": lesson_id,
        "progress": progress,
        "completed_lessons": completed_lessons,
        "certificate_earned": cert_id is not None,
        "certificate_id": cert_id
    }


@api_router.get("/enrollments/{enrollment_id}/lesson-progress")
async def get_lesson_progress(enrollment_id: str, current_user: User = Depends(get_current_user)):
    """Get completed lessons for an enrollment"""
    enrollment = await db.enrollments.find_one({"id": enrollment_id, "user_id": current_user.id})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {
        "enrollment_id": enrollment_id,
        "progress": enrollment.get('progress', 0),
        "completed_lessons": enrollment.get('completed_lessons', []),
        "status": enrollment.get('status', 'active')
    }


# ==================== COUPON ROUTES ====================
@api_router.post("/coupons")
async def create_coupon(coupon_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Check if code already exists
    existing = await db.coupons.find_one({"code": coupon_data['code'].upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Coupon code already exists")
    
    # Parse dates
    valid_from = datetime.fromisoformat(coupon_data['valid_from'])
    valid_until = datetime.fromisoformat(coupon_data['valid_until'])
    
    coupon = Coupon(
        code=coupon_data['code'].upper(),
        discount_type=coupon_data['discount_type'],
        discount_value=float(coupon_data['discount_value']),
        valid_from=valid_from,
        valid_until=valid_until,
        usage_limit=coupon_data.get('usage_limit'),
        applicable_courses=coupon_data.get('applicable_courses'),
        created_by=current_user.id
    )
    
    doc = coupon.model_dump()
    doc['valid_from'] = doc['valid_from'].isoformat()
    doc['valid_until'] = doc['valid_until'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.coupons.insert_one(doc)
    
    return coupon


@api_router.get("/coupons")
async def get_coupons(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    coupons = await db.coupons.find({}, {"_id": 0}).to_list(1000)
    return coupons


@api_router.post("/coupons/validate")
async def validate_coupon(code: str, course_id: str, current_user: User = Depends(get_current_user)):
    """Validate a coupon code for a specific course"""
    coupon = await db.coupons.find_one({"code": code.upper()}, {"_id": 0})
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid coupon code")
    
    if not coupon['is_active']:
        raise HTTPException(status_code=400, detail="Coupon is no longer active")
    
    # Check validity dates
    now = datetime.now(timezone.utc)
    valid_from = datetime.fromisoformat(coupon['valid_from'].replace('Z', '+00:00'))
    valid_until = datetime.fromisoformat(coupon['valid_until'].replace('Z', '+00:00'))
    
    # Ensure timezone awareness
    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=timezone.utc)
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
    
    if now < valid_from:
        raise HTTPException(status_code=400, detail="Coupon is not yet valid")
    
    if now > valid_until:
        raise HTTPException(status_code=400, detail="Coupon has expired")
    
    # Check usage limit
    if coupon['usage_limit'] is not None and coupon['used_count'] >= coupon['usage_limit']:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")
    
    # Check if applicable to course
    if coupon['applicable_courses'] is not None and course_id not in coupon['applicable_courses']:
        raise HTTPException(status_code=400, detail="Coupon not applicable to this course")
    
    # Check if user already used this coupon for this course
    existing_usage = await db.coupon_usage.find_one({
        "coupon_id": coupon['id'],
        "user_id": current_user.id,
        "course_id": course_id
    })
    
    if existing_usage:
        raise HTTPException(status_code=400, detail="You have already used this coupon for this course")
    
    # Get course price
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    original_price = float(course['price'])
    
    # Calculate discount
    if coupon['discount_type'] == 'percentage':
        discount_amount = original_price * (coupon['discount_value'] / 100)
    else:  # fixed
        discount_amount = min(coupon['discount_value'], original_price)
    
    final_price = max(0, original_price - discount_amount)
    
    return {
        "valid": True,
        "coupon": coupon,
        "original_price": original_price,
        "discount_amount": discount_amount,
        "final_price": final_price
    }


@api_router.patch("/coupons/{coupon_id}")
async def update_coupon(coupon_id: str, updates: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.coupons.update_one({"id": coupon_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return {"message": "Coupon updated"}


@api_router.delete("/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.coupons.delete_one({"id": coupon_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    return {"message": "Coupon deleted"}


# ==================== PAYMENT ROUTES ====================
@api_router.post("/payments/checkout")
async def create_checkout(
    course_id: str, 
    request: Request, 
    coupon_code: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already enrolled
    existing = await db.enrollments.find_one({"user_id": current_user.id, "course_id": course_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
    original_price = float(course['price'])
    final_price = original_price
    discount_amount = 0.0
    coupon_id = None
    
    # Apply coupon if provided
    if coupon_code:
        coupon = await db.coupons.find_one({"code": coupon_code.upper()}, {"_id": 0})
        
        if coupon and coupon['is_active']:
            # Validate coupon
            now = datetime.now(timezone.utc)
            valid_from = datetime.fromisoformat(coupon['valid_from'].replace('Z', '+00:00'))
            valid_until = datetime.fromisoformat(coupon['valid_until'].replace('Z', '+00:00'))
            # Ensure timezone awareness
            if valid_from.tzinfo is None:
                valid_from = valid_from.replace(tzinfo=timezone.utc)
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            
            if valid_from <= now <= valid_until:
                if coupon['usage_limit'] is None or coupon['used_count'] < coupon['usage_limit']:
                    if coupon['applicable_courses'] is None or course_id in coupon['applicable_courses']:
                        # Check if user already used this coupon
                        existing_usage = await db.coupon_usage.find_one({
                            "coupon_id": coupon['id'],
                            "user_id": current_user.id,
                            "course_id": course_id
                        })
                        
                        if not existing_usage:
                            # Calculate discount
                            if coupon['discount_type'] == 'percentage':
                                discount_amount = original_price * (coupon['discount_value'] / 100)
                            else:  # fixed
                                discount_amount = min(coupon['discount_value'], original_price)
                            
                            coupon_id = coupon['id']
                            print(f"[DEBUG] Coupon applied: {coupon_code}, Discount: {discount_amount}, Final Price: {original_price - discount_amount}")
                        else:
                            print(f"[DEBUG] Coupon {coupon_code} already used by user {current_user.id}")
                    else:
                        print(f"[DEBUG] Coupon {coupon_code} not applicable to course {course_id}")
                else:
                    print(f"[DEBUG] Coupon {coupon_code} usage limit reached")
            else:
                print(f"[DEBUG] Coupon {coupon_code} expired or not started. Now: {now}, Valid: {valid_from}-{valid_until}")
        else:
            print(f"[DEBUG] Coupon {coupon_code} not found or inactive")

    final_price = max(0.0, original_price - discount_amount)
    print(f"[DEBUG] Checkout Final Calculation - Original: {original_price}, Discount: {discount_amount}, Final: {final_price}")
    
    host_url = str(request.base_url).rstrip('/')
    frontend_url = os.environ.get('FRONTEND_URL', host_url).rstrip('/')
    
    # SPECIAL HANDLING FOR FREE COURSES (Price 0 or 100% Discount)
    if final_price <= 0:
        # Generate internal session ID
        session_id = f"free-{uuid.uuid4()}"
        
        # Create payment record (DIRECTLY PAID)
        payment = Payment(
            user_id=current_user.id,
            course_id=course_id,
            amount=0.0,
            original_amount=original_price,
            discount_amount=discount_amount,
            coupon_code=coupon_code,
            session_id=session_id,
            payment_status="paid"
        )
        payment_doc = payment.model_dump()
        payment_doc['created_at'] = payment_doc['created_at'].isoformat()
        await db.payments.insert_one(payment_doc)
        
        # Create enrollment immediately
        enrollment = Enrollment(user_id=current_user.id, course_id=course_id)
        enroll_doc = enrollment.model_dump()
        enroll_doc['enrolled_at'] = enroll_doc['enrolled_at'].isoformat()
        await db.enrollments.insert_one(enroll_doc)
        
        # Track coupon usage
        if coupon_id:
            coupon_usage = CouponUsage(
                coupon_id=coupon_id,
                user_id=current_user.id,
                course_id=course_id,
                discount_amount=discount_amount
            )
            usage_doc = coupon_usage.model_dump()
            usage_doc['used_at'] = usage_doc['used_at'].isoformat()
            await db.coupon_usage.insert_one(usage_doc)
            
            await db.coupons.update_one(
                {"id": coupon_id},
                {"$inc": {"used_count": 1}}
            )
            
        # Return success URL directly
        success_url = f"{frontend_url}/payment/success?session_id={session_id}"
        return {"url": success_url, "session_id": session_id}

    host_url = str(request.base_url).rstrip('/')
    frontend_url = os.environ.get('FRONTEND_URL', host_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe_key:
        print("CRITICAL ERROR: STRIPE_SECRET_KEY is missing from environment variables!")
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: Stripe API Key is missing. Please set STRIPE_SECRET_KEY in your environment variables."
        )

    stripe_checkout = StripeCheckout(
        api_key=stripe_key,
        webhook_url=webhook_url
    )
    
    success_url = f"{frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{frontend_url}/payment/cancel"
    
    checkout_request = CheckoutSessionRequest(
        amount=final_price,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user.id,
            "course_id": course_id,
            "user_email": current_user.email,
            "coupon_code": coupon_code or "",
            "original_price": str(original_price),
            "discount_amount": str(discount_amount)
        }
    )
    
    # NEW: Fetch instructor's Stripe account for payment splitting
    instructor_stripe_id = None
    try:
        instructor = await db.instructors.find_one({"id": course['instructor_id']})
        if instructor and instructor.get('stripe_account_id'):
            instructor_stripe_id = instructor['stripe_account_id']
            print(f"[DEBUG] Payment splitting enabled for instructor {instructor['id']}: {instructor_stripe_id}")
        else:
            print(f"[DEBUG] No Stripe account for instructor {course['instructor_id']}, 100% to platform")
    except Exception as e:
        print(f"[DEBUG] Error fetching instructor Stripe account: {e}")
        # Continue with 100% to platform if error occurs
    
    session = await stripe_checkout.create_checkout_session(
        checkout_request, 
        instructor_stripe_account_id=instructor_stripe_id
    )
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        course_id=course_id,
        amount=final_price,
        original_amount=original_price,
        discount_amount=discount_amount,
        coupon_code=coupon_code,
        session_id=session.session_id,
        payment_status="pending"
    )
    payment_doc = payment.model_dump()
    payment_doc['created_at'] = payment_doc['created_at'].isoformat()
    await db.payments.insert_one(payment_doc)
    
    # If coupon was applied, track usage (will increment count after successful payment)
    if coupon_id:
        coupon_usage = CouponUsage(
            coupon_id=coupon_id,
            user_id=current_user.id,
            course_id=course_id,
            discount_amount=discount_amount
        )
        usage_doc = coupon_usage.model_dump()
        usage_doc['used_at'] = usage_doc['used_at'].isoformat()
        await db.coupon_usage.insert_one(usage_doc)
        
        # Increment coupon usage count
        await db.coupons.update_one(
            {"id": coupon_id},
            {"$inc": {"used_count": 1}}
        )
    
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/payments/status/{session_id}")
async def check_payment_status(session_id: str, current_user: User = Depends(get_current_user)):
    # Internal Free Session Check
    if session_id.startswith("free-"):
        payment = await db.payments.find_one({"session_id": session_id})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return {"payment_status": "paid", "session_id": session_id}

    stripe_checkout = StripeCheckout(
        api_key=os.environ.get('STRIPE_SECRET_KEY'),
        webhook_url=""
    )
    
    status = await stripe_checkout.get_checkout_status(session_id)
    
    payment = await db.payments.find_one({"session_id": session_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Support both "paid" and "no_payment_required" (for 100% coupons)
    valid_statuses = ["paid", "no_payment_required"]
    if status.payment_status in valid_statuses:
        if payment['payment_status'] != 'paid':
            await db.payments.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": "paid"}}
            )
            
            # Create enrollment
            enrollment = Enrollment(user_id=payment['user_id'], course_id=payment['course_id'])
            enroll_doc = enrollment.model_dump()
            enroll_doc['enrolled_at'] = enroll_doc['enrolled_at'].isoformat()
            await db.enrollments.insert_one(enroll_doc)
            
            # Update instructor earnings
            course = await db.courses.find_one({"id": payment['course_id']})
            if course:
                instructor_share = payment['amount'] * (1 - ADMIN_COMMISSION)
                await db.instructors.update_one(
                    {"id": course['instructor_id']},
                    {"$inc": {"earnings": instructor_share}}
                )
        
        # Normalize status for frontend
        status.payment_status = "paid"
        
    # Ensure metadata has the course_id from our database record if missing from Stripe
    if not status.metadata.get('course_id') and payment:
        status.metadata['course_id'] = payment.get('course_id')
    
    return status


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    stripe_checkout = StripeCheckout(
        api_key=os.environ.get('STRIPE_SECRET_KEY'),
        webhook_url=""
    )
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        return {"received": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== STRIPE CONNECT OAUTH ====================
@api_router.get("/payments/stripe/connect")
async def stripe_connect_oauth(current_user: User = Depends(get_current_user)):
    """Generate Stripe Connect OAuth URL for instructors"""
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Only instructors can connect Stripe accounts")
    
    # Get Stripe client ID from environment
    client_id = os.environ.get('STRIPE_CLIENT_ID')
    if not client_id:
        raise HTTPException(
            status_code=500,
            detail="Stripe Connect not configured. Please set STRIPE_CLIENT_ID."
        )
    
    # Generate OAuth URL
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    redirect_uri = f"{frontend_url}/api/payments/stripe/callback"
    
    oauth_url = (
        f"https://connect.stripe.com/oauth/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&scope=read_write"
        f"&redirect_uri={redirect_uri}"
        f"&state={current_user.id}"  # Pass user ID to identify after redirect
    )
    
    return {"url": oauth_url}


@api_router.get("/payments/stripe/callback")
async def stripe_connect_callback(code: str, state: str):
    """Handle Stripe OAuth callback and save instructor's stripe_account_id"""
    try:
        # Exchange authorization code for stripe_user_id
        client_secret = os.environ.get('STRIPE_SECRET_KEY')
        
        response = stripe.OAuth.token(
            grant_type='authorization_code',
            code=code,
        )
        
        stripe_account_id = response['stripe_user_id']
        user_id = state  # user_id passed via state parameter
        
        # Update instructor's Stripe account ID
        instructor = await db.instructors.find_one({"user_id": user_id})
        if not instructor:
            raise HTTPException(status_code=404, detail="Instructor profile not found")
        
        await db.instructors.update_one(
            {"user_id": user_id},
            {"$set": {"stripe_account_id": stripe_account_id}}
        )
        
        logger.info(f"Stripe account connected for instructor {instructor['id']}: {stripe_account_id}")
        
        # Redirect to instructor settings with success message
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/dashboard/instructor?stripe_connected=true")
        
    except stripe.oauth_error.OAuthError as e:
        logger.error(f"Stripe OAuth error: {e}")
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/dashboard/instructor?stripe_error=true")
    except Exception as e:
        logger.error(f"Error in Stripe callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/payments/stripe/status")
async def get_stripe_connection_status(current_user: User = Depends(get_current_user)):
    """Check if current instructor has connected Stripe account"""
    if current_user.role not in ["instructor", "admin"]:
        return {"connected": False, "message": "Not an instructor"}
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor:
        return {"connected": False, "message": "Instructor profile not found"}
    
    stripe_account_id = instructor.get('stripe_account_id')
    
    return {
        "connected": bool(stripe_account_id),
        "stripe_account_id": stripe_account_id if stripe_account_id else None
    }


# ==================== TEST ENDPOINT (DEVELOPMENT ONLY) ====================
@api_router.get("/test-split")
async def test_payment_split():
    """
    Test endpoint to verify Stripe payment splitting logic.
    Returns the session data to inspect payment_intent_data.
    """
    try:
        # Hardcoded test values
        test_price = 100.00  # $100
        test_instructor_stripe_id = "acct_123456789"  # Dummy Stripe account
        
        # Get Stripe key
        stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        if not stripe_key:
            return {"error": "STRIPE_SECRET_KEY not configured"}
        
        # Create Stripe checkout instance
        stripe_checkout = StripeCheckout(
            api_key=stripe_key,
            webhook_url=""
        )
        
        # Prepare test checkout request
        checkout_request = CheckoutSessionRequest(
            amount=test_price,
            currency="usd",
            success_url="http://localhost:3000/test-success",
            cancel_url="http://localhost:3000/test-cancel",
            metadata={
                "test": "true",
                "course_id": "test-course-123"
            }
        )
        
        # Call create_checkout_session with instructor Stripe ID
        session = await stripe_checkout.create_checkout_session(
            checkout_request,
            instructor_stripe_account_id=test_instructor_stripe_id
        )
        
        # Retrieve full session from Stripe to inspect payment_intent_data
        full_session = stripe.checkout.Session.retrieve(session.session_id)
        
        # Return relevant data for verification
        return {
            "test_configuration": {
                "price": test_price,
                "price_in_cents": int(test_price * 100),
                "instructor_stripe_id": test_instructor_stripe_id,
                "expected_platform_fee": int(test_price * 100 * 0.10),
                "expected_instructor_amount": int(test_price * 100 * 0.90)
            },
            "session_data": {
                "session_id": full_session.id,
                "amount_total": full_session.amount_total,
                "payment_intent": full_session.payment_intent,
                "mode": full_session.mode,
                "status": full_session.status
            },
            "payment_intent_details": {
                "note": "Check Stripe Dashboard for payment_intent details",
                "payment_intent_id": full_session.payment_intent,
                "expected_application_fee_amount": 1000,  # 10% of $100 = $10 = 1000 cents
                "expected_transfer_destination": test_instructor_stripe_id
            },
            "verification": {
                "instructions": [
                    "1. Copy the payment_intent ID from above",
                    "2. Go to Stripe Dashboard > Payments > Search for payment_intent",
                    "3. Check 'Application fee' = $10.00",
                    "4. Check 'Transfer destination' = acct_123456789",
                    "Or use Stripe CLI: stripe payment_intents retrieve <payment_intent_id>"
                ]
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "note": "Make sure STRIPE_SECRET_KEY is set and valid"
        }



# ==================== AI ROUTES ====================
@api_router.post("/ai/course-assistant")
async def ai_course_assistant(prompt: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Instructor only")
    
    chat = LlmChat(
        api_key=os.environ.get('GROQ_API_KEY'),
        session_id=f"assistant-{current_user.id}",
        system_message="You are an AI assistant helping instructors create course content. Provide helpful suggestions for course descriptions, lesson titles, and quiz questions."
    ).with_model("groq", "llama-70b")
    
    message = UserMessage(text=prompt)
    response = await chat.send_message(message)
    return {"response": response}


@api_router.post("/upload/thumbnail")
async def upload_thumbnail(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Instructor only")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        file_extension = Path(file.filename).suffix
        if not file_extension:
            file_extension = ".png" # Default
            
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = THUMBNAIL_DIR / unique_filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        return {"url": f"/uploads/thumbnails/{unique_filename}"}
    except Exception as e:
        logging.error(f"Thumbnail upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload thumbnail")


@api_router.post("/upload/lesson-pdf")
async def upload_lesson_pdf(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Instructor only")
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        unique_filename = f"{uuid.uuid4()}.pdf"
        file_path = PDF_DIR / unique_filename
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            
        return {"url": f"/uploads/pdfs/{unique_filename}"}
    except Exception as e:
        logging.error(f"PDF upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload PDF")


@api_router.post("/ai/tutor")
async def ai_tutor(course_id: str, question: str, current_user: User = Depends(get_current_user)):
    # Check enrollment
    enrollment = await db.enrollments.find_one({"user_id": current_user.id, "course_id": course_id})
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course")
    
    # Get course context
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    lessons = await db.lessons.find({"course_id": course_id}, {"_id": 0}).to_list(100)
    
    context = f"Course: {course['title']}\nDescription: {course['description']}\n\n"
    context += "Lessons:\n" + "\n".join([f"- {l['title']}" for l in lessons])
    
    chat = LlmChat(
        api_key=os.environ.get('GROQ_API_KEY'),
        session_id=f"tutor-{current_user.id}-{course_id}",
        system_message=f"You are an AI tutor for this course. Help students understand the material.\n\n{context}"
    ).with_model("groq", "llama-70b")
    
    message = UserMessage(text=question)
    response = await chat.send_message(message)
    return {"response": response}


@api_router.get("/ai/recommendations")
async def get_recommendations(current_user: User = Depends(get_current_user)):
    enrollments = await db.enrollments.find({"user_id": current_user.id}, {"_id": 0}).to_list(100)
    enrolled_ids = [e['course_id'] for e in enrollments]
    
    if not enrolled_ids:
        # Return popular courses
        courses = await db.courses.find({"status": "published"}, {"_id": 0}).limit(5).to_list(5)
        return courses
    
    # Get enrolled course categories
    enrolled_courses = await db.courses.find({"id": {"$in": enrolled_ids}}, {"_id": 0}).to_list(100)
    categories = list(set([c['category'] for c in enrolled_courses]))
    
    # Find similar courses
    recommended = await db.courses.find({
        "status": "published",
        "category": {"$in": categories},
        "id": {"$nin": enrolled_ids}
    }, {"_id": 0}).limit(5).to_list(5)
    
    return recommended


# ==================== ADMIN ROUTES ====================
@api_router.get("/admin/analytics")
async def get_analytics(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    total_users = await db.users.count_documents({})
    total_courses = await db.courses.count_documents({"status": "published"})
    total_enrollments = await db.enrollments.count_documents({})
    
    # Calculate total revenue
    payments = await db.payments.find({"payment_status": "paid"}, {"_id": 0}).to_list(10000)
    total_revenue = sum([p['amount'] for p in payments])
    
    return {
        "total_users": total_users,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "total_revenue": total_revenue,
        "admin_earnings": total_revenue * ADMIN_COMMISSION
    }


@api_router.get("/admin/users")
async def get_all_users(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(10000)
    return users


@api_router.patch("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, new_role: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    if new_role not in ["student", "instructor", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": new_role}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User role updated to {new_role}"}


@api_router.patch("/admin/users/{user_id}/status")
async def toggle_user_status(user_id: str, active: bool, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Add is_active field to user document
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": active}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    status = "activated" if active else "deactivated"
    return {"message": f"User {status}"}


@api_router.get("/admin/courses/pending")
async def get_pending_courses(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Get all courses that are in draft status
    courses = await db.courses.find({"status": "draft"}, {"_id": 0}).to_list(1000)
    
    # Enrich with instructor information
    enriched_courses = []
    for course in courses:
        instructor = await db.instructors.find_one({"id": course['instructor_id']}, {"_id": 0})
        if instructor:
            user = await db.users.find_one({"id": instructor['user_id']}, {"_id": 0, "password": 0})
            course['instructor_name'] = user.get('name', 'Unknown') if user else 'Unknown'
            course['instructor_email'] = user.get('email', 'Unknown') if user else 'Unknown'
        enriched_courses.append(course)
    
    return enriched_courses


@api_router.patch("/admin/courses/{course_id}/moderate")
async def moderate_course(course_id: str, approved: bool, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_status = "published" if approved else "draft"
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"status": new_status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"message": f"Course status updated to {new_status}"}


@api_router.patch("/admin/courses/{course_id}/feature")
async def toggle_featured_course(course_id: str, featured: bool, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"is_featured": featured}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    
    status = "featured" if featured else "unfeatured"
    return {"message": f"Course {status}"}


@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Don't allow deleting yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Clean up related data
    await db.instructors.delete_many({"user_id": user_id})
    await db.enrollments.delete_many({"user_id": user_id})
    
    return {"message": "User deleted successfully"}



# ==================== QUIZ ROUTES ====================
@api_router.post("/quizzes")
async def create_quiz(quiz_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Instructor only")
    
    course = await db.courses.find_one({"id": quiz_data['course_id']})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    quiz = Quiz(**quiz_data)
    doc = quiz.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.quizzes.insert_one(doc)
    return quiz


@api_router.get("/quizzes/{course_id}")
async def get_quizzes(course_id: str, request: Request):
    current_user = await get_optional_user(request)
    is_authorized = False
    
    if current_user:
        if current_user.role == "admin":
            is_authorized = True
        else:
            course = await db.courses.find_one({"id": course_id})
            if course:
                instructor = await db.instructors.find_one({"user_id": current_user.id})
                if instructor and instructor['id'] == course.get('instructor_id'):
                    is_authorized = True
            
            if not is_authorized:
                is_authorized = await check_enrollment_status(current_user.id, course_id)
                
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Enrollment required to access quizzes")

    quizzes = await db.quizzes.find({"course_id": course_id}, {"_id": 0}).to_list(1000)
    return quizzes


@api_router.delete("/quizzes/{quiz_id}")
async def delete_quiz(quiz_id: str, current_user: User = Depends(get_current_user)):
    quiz = await db.quizzes.find_one({"id": quiz_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    course = await db.courses.find_one({"id": quiz['course_id']})
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.quizzes.delete_one({"id": quiz_id})
    return {"message": "Quiz deleted"}


@api_router.patch("/quizzes/{quiz_id}")
async def update_quiz(quiz_id: str, quiz_data: dict, current_user: User = Depends(get_current_user)):
    quiz = await db.quizzes.find_one({"id": quiz_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    course = await db.courses.find_one({"id": quiz['course_id']})
    # Allow Admin or Owner
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    else:
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if instructor and instructor['id'] == course['instructor_id']:
            is_authorized = True
            
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update quiz fields
    update_data = {}
    if 'title' in quiz_data:
        update_data['title'] = quiz_data['title']
    if 'questions' in quiz_data:
        update_data['questions'] = quiz_data['questions']
    
    if not update_data:
        return quiz

    await db.quizzes.update_one({"id": quiz_id}, {"$set": update_data})
    
    updated_quiz = await db.quizzes.find_one({"id": quiz_id}, {"_id": 0})
    return updated_quiz


@api_router.post("/quizzes/{quiz_id}/submit")
async def submit_quiz(quiz_id: str, answers: List[int], current_user: User = Depends(get_current_user)):
    quiz = await db.quizzes.find_one({"id": quiz_id}, {"_id": 0})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Calculate score
    correct = 0
    for i, answer in enumerate(answers):
        if i < len(quiz['questions']) and quiz['questions'][i]['correct_answer'] == answer:
            correct += 1
    
    score = (correct / len(quiz['questions'])) * 100 if quiz['questions'] else 0
    
    # Save result
    result = QuizResult(
        user_id=current_user.id,
        quiz_id=quiz_id,
        course_id=quiz['course_id'],
        score=score
    )
    doc = result.model_dump()
    doc['submitted_at'] = doc['submitted_at'].isoformat()
    await db.quiz_results.insert_one(doc)
    
    # Check if user is eligible for certificate after quiz submission
    cert_id = await generate_certificate_if_eligible(current_user.id, quiz['course_id'])
    certificate_earned = cert_id is not None
    
    return {
        "score": score,
        "correct": correct,
        "total": len(quiz['questions']),
        "certificate_earned": certificate_earned,
        "certificate_id": cert_id
    }




# ==================== HELPER FUNCTIONS ====================
def generate_certificate_pdf(user_name: str, course_title: str, completion_date: str, certificate_id: str) -> bytes:
    """Generate a professional certificate PDF"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Background border
    c.setStrokeColor(colors.HexColor('#10b981'))
    c.setLineWidth(10)
    c.rect(30, 30, width - 60, height - 60)
    
    # Inner border
    c.setStrokeColor(colors.HexColor('#059669'))
    c.setLineWidth(2)
    c.rect(50, 50, width - 100, height - 100)
    
    # Title
    c.setFont("Helvetica-Bold", 48)
    c.setFillColor(colors.HexColor('#10b981'))
    c.drawCentredString(width / 2, height - 120, "Certificate")
    
    c.setFont("Helvetica", 28)
    c.setFillColor(colors.HexColor('#374151'))
    c.drawCentredString(width / 2, height - 160, "of Completion")
    
    # Divider line
    c.setStrokeColor(colors.HexColor('#d1fae5'))
    c.setLineWidth(2)
    c.line(150, height - 190, width - 150, height - 190)
    
    # Presented to text
    c.setFont("Helvetica", 18)
    c.setFillColor(colors.HexColor('#6b7280'))
    c.drawCentredString(width / 2, height - 240, "This certificate is presented to")
    
    # Student name
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(colors.HexColor('#1a1a1a'))
    c.drawCentredString(width / 2, height - 300, user_name)
    
    # Achievement text
    c.setFont("Helvetica", 16)
    c.setFillColor(colors.HexColor('#6b7280'))
    c.drawCentredString(width / 2, height - 350, "for successfully completing the course")
    
    # Course title
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor('#10b981'))
    c.drawCentredString(width / 2, height - 400, course_title)
    
    # Completion date
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor('#6b7280'))
    c.drawCentredString(width / 2, height - 470, f"Completed on {completion_date}")
    
    # Certificate ID
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor('#9ca3af'))
    c.drawCentredString(width / 2, 100, f"Certificate ID: {certificate_id}")
    
    # Platform name
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor('#10b981'))
    c.drawCentredString(width / 2, 140, "LearnHub")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


async def check_certificate_eligibility(user_id: str, course_id: str) -> tuple[bool, str]:
    """Check if user is eligible for certificate (100% completion + all quizzes passed)"""
    # Check enrollment and progress
    enrollment = await db.enrollments.find_one({"user_id": user_id, "course_id": course_id})
    if not enrollment or enrollment['progress'] < 100:
        return False, "Course not completed"
    
    # Get all quizzes for the course
    quizzes = await db.quizzes.find({"course_id": course_id}, {"_id": 0}).to_list(1000)
    
    if quizzes:
        # Check if all quizzes are passed (score >= 70)
        for quiz in quizzes:
            quiz_result = await db.quiz_results.find_one({
                "user_id": user_id,
                "quiz_id": quiz['id']
            })
            if not quiz_result or quiz_result['score'] < 70:
                return False, f"Quiz '{quiz['title']}' not passed (minimum 70% required)"
    
    return True, "Eligible"


async def generate_certificate_if_eligible(user_id: str, course_id: str):
    """Auto-generate certificate if user is eligible"""
    # Check if certificate already exists
    existing = await db.certificates.find_one({"user_id": user_id, "course_id": course_id})
    if existing:
        return existing['id']
    
    # Check eligibility
    eligible, message = await check_certificate_eligibility(user_id, course_id)
    if not eligible:
        return None
    
    # Create certificate
    certificate = Certificate(user_id=user_id, course_id=course_id)
    doc = certificate.model_dump()
    doc['issued_date'] = doc['issued_date'].isoformat()
    await db.certificates.insert_one(doc)
    
    return certificate.id


# ==================== CERTIFICATE ROUTES ====================
@api_router.get("/certificates/my-certificates")
async def get_my_certificates(current_user: User = Depends(get_current_user)):
    certificates = await db.certificates.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    result = []
    for cert in certificates:
        course = await db.courses.find_one({"id": cert['course_id']}, {"_id": 0})
        if course:
            result.append({**cert, "course": course})
    
    return result


@api_router.get("/certificates/{certificate_id}")
async def get_certificate(certificate_id: str):
    cert = await db.certificates.find_one({"id": certificate_id}, {"_id": 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    user = await db.users.find_one({"id": cert['user_id']}, {"_id": 0, "password": 0})
    course = await db.courses.find_one({"id": cert['course_id']}, {"_id": 0})
    
    return {**cert, "user": user, "course": course}


@api_router.get("/certificates/{certificate_id}/download")
async def download_certificate(certificate_id: str):
    cert = await db.certificates.find_one({"id": certificate_id}, {"_id": 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    user = await db.users.find_one({"id": cert['user_id']}, {"_id": 0, "password": 0})
    course = await db.courses.find_one({"id": cert['course_id']}, {"_id": 0})
    
    if not user or not course:
        raise HTTPException(status_code=404, detail="User or course not found")
    
    # Generate PDF
    completion_date = datetime.fromisoformat(cert['issued_date']).strftime("%B %d, %Y")
    pdf_bytes = generate_certificate_pdf(
        user_name=user['name'],
        course_title=course['title'],
        completion_date=completion_date,
        certificate_id=certificate_id
    )
    
    # Save to temp file and return (cross-platform)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"certificate_{certificate_id}.pdf")
    with open(temp_path, "wb") as f:
        f.write(pdf_bytes)
    
    return FileResponse(
        temp_path,
        media_type="application/pdf",
        filename=f"Certificate_{course['title'].replace(' ', '_')}.pdf"
    )


@api_router.post("/certificates/check-eligibility/{course_id}")
async def check_eligibility(course_id: str, current_user: User = Depends(get_current_user)):
    eligible, message = await check_certificate_eligibility(current_user.id, course_id)
    
    if eligible:
        # Auto-generate certificate if eligible
        cert_id = await generate_certificate_if_eligible(current_user.id, course_id)
        return {"eligible": True, "certificate_id": cert_id, "message": "Certificate generated!"}
    else:
        return {"eligible": False, "message": message}



# ==================== REVIEW ROUTES ====================
@api_router.post("/reviews")
async def create_review(review_data: dict, current_user: User = Depends(get_current_user)):
    # Check if user is enrolled
    enrollment = await db.enrollments.find_one({
        "user_id": current_user.id,
        "course_id": review_data['course_id']
    })
    if not enrollment:
        raise HTTPException(status_code=403, detail="Must be enrolled to review")
    
    # Check if user already reviewed
    existing = await db.reviews.find_one({
        "user_id": current_user.id,
        "course_id": review_data['course_id']
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already reviewed this course")
    
    # Validate rating
    if review_data['rating'] < 1 or review_data['rating'] > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    review = Review(
        user_id=current_user.id,
        course_id=review_data['course_id'],
        rating=review_data['rating'],
        review_text=review_data.get('review_text')
    )
    doc = review.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.reviews.insert_one(doc)
    
    return review


@api_router.get("/reviews/{course_id}")
async def get_reviews(course_id: str):
    reviews = await db.reviews.find({"course_id": course_id}, {"_id": 0}).to_list(1000)
    
    # Enrich with user info
    enriched = []
    for review in reviews:
        user = await db.users.find_one({"id": review['user_id']}, {"_id": 0, "password": 0})
        if user:
            enriched.append({
                **review,
                "user_name": user['name'],
                "user_image": user.get('profile_image')
            })
    
    return enriched


@api_router.get("/reviews/{course_id}/average")
async def get_average_rating(course_id: str):
    reviews = await db.reviews.find({"course_id": course_id}, {"_id": 0}).to_list(1000)
    
    if not reviews:
        return {"average_rating": 0, "total_reviews": 0}
    
    total_rating = sum(r['rating'] for r in reviews)
    average = total_rating / len(reviews)
    
    return {"average_rating": round(average, 1), "total_reviews": len(reviews)}


@api_router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, current_user: User = Depends(get_current_user)):
    review = await db.reviews.find_one({"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Only owner or admin can delete
    if review['user_id'] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.reviews.delete_one({"id": review_id})
    return {"message": "Review deleted"}



# Static Files
UPLOAD_DIR = ROOT_DIR / "uploads"
THUMBNAIL_DIR = UPLOAD_DIR / "thumbnails"
PDF_DIR = UPLOAD_DIR / "pdfs"
UPLOAD_DIR.mkdir(exist_ok=True)
THUMBNAIL_DIR.mkdir(exist_ok=True)
PDF_DIR.mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Note: Router is included at the very end of the file after all routes are defined


# Define allowed origins (Localhost + Your Domain + Railway)
origins = [
    "http://localhost:3000",
    "https://britsyncaiacademy.online",
    "http://britsyncaiacademy.online",
    "https://learnhub-production-3604.up.railway.app",
    "*"  # Optional: Allows everyone (good for debugging, remove later for security)
]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    return {"message": "LearnHub Backend is running", "docs": "/docs"}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"message": "LearnHub Backend is running", "docs": "/docs"}

@app.get("/fix-my-account")
async def fix_my_account(email: str):
    try:
        results = []
        
        # 1. Find specific user (Simulate Login query which we know works)
        user = await db.users.find_one({"email": email})
        if not user:
            return {"status": "Error", "details": f"User with email '{email}' not found. Please register first."}
            
        uid = user['id']
        results.append(f"Found User: {email} (ID: {uid})")
        
        # Force Admin
        await db.users.update_one({"id": uid}, {"$set": {"role": "admin"}})
        results.append("Role -> ADMIN")
        
        # Check/Fix instructor
        instructor = await db.instructors.find_one({"user_id": uid})
        if not instructor:
            # Create a real instructor record
            results.append("Creating Instructor Profile")
            new_id = str(uuid.uuid4())
            new_instructor = {
                "id": new_id,
                "user_id": uid,
                "bio": "Auto-fixed",
                "verification_status": "approved",
                "earnings": 0.0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.instructors.insert_one(new_instructor)
            inst_id = new_id
        else:
            inst_id = instructor.get('id')
            if not inst_id:
                inst_id = str(uuid.uuid4())
                await db.instructors.update_one({"user_id": uid}, {"$set": {"id": inst_id}})
                results.append(f"Fixed missing ID for Instructor: {inst_id}")

            await db.instructors.update_one(
                {"user_id": uid},
                {"$set": {"verification_status": "approved"}}
            )
            results.append("Instructor -> APPROVED")

        # 3. Fix existing courses for this instructor if they have 'undefined' or missing ID
        course_fix = await db.courses.update_many(
            {"instructor_id": {"$in": [None, "undefined", "null", ""]}},
            {"$set": {"instructor_id": inst_id}}
        )
        if course_fix.modified_count > 0:
            results.append(f"Fixed {course_fix.modified_count} orphaned courses")
        
        return {"status": "Success", "details": results}

    except Exception as e:
        logger.error(f"Fix account failed: {e}")
        return {"status": "Error", "error": str(e)}


@app.get("/fix-coupons")
async def fix_coupons():
    """Fix coupon validity dates to be currently valid"""
    try:
        now = datetime.now(timezone.utc)
        # Set valid_from to yesterday and valid_until to 1 year from now
        valid_from = (now - timedelta(days=1)).isoformat()
        valid_until = (now + timedelta(days=365)).isoformat()
        
        result = await db.coupons.update_many(
            {},
            {"$set": {
                "valid_from": valid_from,
                "valid_until": valid_until,
                "is_active": True
            }}
        )
        
        return {
            "message": f"Fixed {result.modified_count} coupons",
            "valid_from": valid_from,
            "valid_until": valid_until
        }
    except Exception as e:
        logger.error(f"Fix coupons failed: {e}")
        return {"status": "Error", "error": str(e)}


@api_router.get("/debug/courses")
async def debug_courses():

    """Temporary diagnostic endpoint"""
    courses = await db.courses.find({}, {"_id": 0}).to_list(100)
    return courses

@app.get("/payment/success")
async def payment_success_redirect(session_id: str):
    """
    Handle Stripe redirect to backend and forward to frontend.
    This fixes the 404 error when FRONTEND_URL is not directly used in success_url.
    """
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
    logger.info(f"Redirecting success session {session_id} to {frontend_url}")
    return RedirectResponse(url=f"{frontend_url}/payment/success?session_id={session_id}")


@app.get("/payment/cancel")
async def payment_cancel_redirect():
    """Handle Stripe cancel redirect to backend and forward to frontend."""
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
    logger.info(f"Redirecting cancellation to {frontend_url}")
    return RedirectResponse(url=f"{frontend_url}/payment/cancel")


# ==================== NEWSLETTER ENDPOINTS ====================
@api_router.post("/newsletter/subscribe")
async def subscribe_newsletter(email: EmailStr):
    """Subscribe to weekly newsletter"""
    try:
        existing = await db.email_subscriptions.find_one({"email": email})
        if existing and existing['subscribed']:
            return {"message": "Already subscribed", "success": False}
        
        if existing:
            await db.email_subscriptions.update_one(
                {"email": email},
                {"$set": {"subscribed": True}}
            )
        else:
            doc = {
                "id": str(uuid.uuid4()),
                "email": email,
                "subscribed": True,
                "unsubscribe_token": str(uuid.uuid4()),
                "subscription_date": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.email_subscriptions.insert_one(doc)
        
        return {"message": "Subscribed successfully!", "success": True}
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe")


@api_router.get("/newsletter/unsubscribe")
async def unsubscribe_newsletter(token: str):
    """Unsubscribe from newsletter"""
    try:
        result = await db.email_subscriptions.update_one(
            {"unsubscribe_token": token},
            {"$set": {"subscribed": False}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Invalid token")
        
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/unsubscribe-success")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")


@api_router.get("/blog/posts")
async def get_blog_posts(limit: int = 3):
    """Get latest blog posts"""
    try:
        posts = await db.blog_posts.find(
            {"status": "published"},
            sort=[("published_at", -1)]
        ).limit(limit).to_list(limit)
        return posts
    except Exception as e:
        logger.error(f"Blog fetch error: {e}")
        return []


@api_router.post("/admin/newsletter/generate")
async def generate_newsletter(current_user: User = Depends(get_current_user)):
    """Generate weekly blog (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    blog = await newsletter.generate_weekly_blog(db)
    if blog:
        return {"message": "Blog generated", "title": blog.get("title")}
    return {"message": "Failed to generate blog"}


@api_router.post("/admin/newsletter/send")
async def send_newsletter_now(current_user: User = Depends(get_current_user)):
    """Send newsletter to subscribers (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await newsletter.send_weekly_newsletter(db)
    return result


# Include router AFTER all routes are defined
app.include_router(api_router)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

