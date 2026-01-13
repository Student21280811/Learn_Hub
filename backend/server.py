from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import tempfile
import logging
from pathlib import Path
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
import os
from dotenv import load_dotenv

load_dotenv() # Load the .env file

# Set the key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    thumbnail: Optional[str] = None
    status: str = "draft"  # draft, published, archived, rejected
    video_platform: Optional[str] = "youtube"  # youtube, vimeo
    preview_video: Optional[str] = None
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
    user_doc = user.model_dump()
    user_doc['password'] = hashed_pw
    user_doc['created_at'] = user_doc['created_at'].isoformat()
    
    await db.users.insert_one(user_doc)
    
    # AUTO-CREATE INSTRUCTOR DOCUMENT if user registers as instructor
    if user.role == "instructor":
        instructor = Instructor(
            user_id=user.id,
            verification_status="pending",
            bio="Pending approval"
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
    token = create_access_token({"sub": user.id, "role": user.role})
    return {"token": token, "user": user}


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
    
    instructor = Instructor(user_id=current_user.id, bio=bio)
    doc = instructor.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.instructors.insert_one(doc)
    
    # Update user role
    await db.users.update_one({"id": current_user.id}, {"$set": {"role": "instructor"}})
    
    return {"message": "Application submitted for review", "instructor": instructor}


@api_router.get("/instructors")
async def get_instructors(status: Optional[str] = None):
    query = {}
    if status:
        query['verification_status'] = status
    instructors = await db.instructors.find(query, {"_id": 0}).to_list(1000)
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
    
    return {"message": f"Instructor {new_status}"}


# ==================== COURSE ROUTES ====================
@api_router.post("/courses", response_model=Course)
async def create_course(course_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Only instructors and admins can create courses")
    
    instructor_id = None
    if current_user.role == "admin":
        # For admin, we use their user_id as instructor_id or find their instructor profile if it exists
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if not instructor:
            # Create a virtual instructor record for the admin if missing
            instructor_id = f"admin-inst-{current_user.id}"
        else:
            instructor_id = instructor['id']
    else:
        # Regular instructor must be approved
        instructor = await db.instructors.find_one({"user_id": current_user.id})
        if not instructor or instructor.get('verification_status') != 'approved':
            raise HTTPException(status_code=403, detail="Your instructor profile is not yet approved")
        instructor_id = instructor['id']
    
    try:
        course = Course(instructor_id=instructor_id, **course_data)
        doc = course.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.courses.insert_one(doc)
        return course
    except Exception as e:
        logging.error(f"Course creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error during course creation: {str(e)}")


@api_router.get("/courses")
async def get_courses(
    category: Optional[str] = None,
    status: Optional[str] = "published",
    search: Optional[str] = None,
    instructor_id: Optional[str] = None
):
    query = {}
    if category:
        query['category'] = category
    if status and status != 'all':
        query['status'] = status
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
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor or instructor['id'] != course['instructor_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.courses.update_one({"id": course_id}, {"$set": updates})
    return {"message": "Course updated"}


@api_router.post("/courses/{course_id}/lessons")
async def add_lesson(course_id: str, lesson_data: dict, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor or instructor['id'] != course['instructor_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    lesson = Lesson(course_id=course_id, **lesson_data)
    doc = lesson.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.lessons.insert_one(doc)
    return lesson


@api_router.get("/courses/{course_id}/lessons")
async def get_lessons(course_id: str):
    lessons = await db.lessons.find({"course_id": course_id}, {"_id": 0}).sort("order", 1).to_list(1000)
    return lessons


# ==================== SECTION ROUTES ====================
@api_router.post("/courses/{course_id}/sections")
async def create_section(course_id: str, section_data: dict, current_user: User = Depends(get_current_user)):
    course = await db.courses.find_one({"id": course_id})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor or instructor['id'] != course['instructor_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    section = Section(course_id=course_id, **section_data)
    doc = section.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.sections.insert_one(doc)
    return section


@api_router.get("/courses/{course_id}/sections")
async def get_sections(course_id: str):
    sections = await db.sections.find({"course_id": course_id}, {"_id": 0}).sort("order", 1).to_list(1000)
    
    # Get lessons for each section
    for section in sections:
        lessons = await db.lessons.find({"section_id": section['id']}, {"_id": 0}).sort("order", 1).to_list(1000)
        section['lessons'] = lessons
    
    return sections


@api_router.delete("/sections/{section_id}")
async def delete_section(section_id: str, current_user: User = Depends(get_current_user)):
    section = await db.sections.find_one({"id": section_id})
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    course = await db.courses.find_one({"id": section['course_id']})
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    
    if not instructor or instructor['id'] != course['instructor_id']:
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
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor or instructor['id'] != course['instructor_id']:
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
async def get_live_classes(course_id: str):
    live_classes = await db.live_classes.find({"course_id": course_id}, {"_id": 0}).sort("scheduled_at", 1).to_list(1000)
    return live_classes


@api_router.patch("/live-classes/{live_class_id}")
async def update_live_class(live_class_id: str, updates: dict, current_user: User = Depends(get_current_user)):
    live_class = await db.live_classes.find_one({"id": live_class_id})
    if not live_class:
        raise HTTPException(status_code=404, detail="Live class not found")
    
    course = await db.courses.find_one({"id": live_class['course_id']})
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    
    if not instructor or instructor['id'] != course['instructor_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.live_classes.update_one({"id": live_class_id}, {"$set": updates})
    return {"message": "Live class updated"}


@api_router.delete("/live-classes/{live_class_id}")
async def delete_live_class(live_class_id: str, current_user: User = Depends(get_current_user)):
    live_class = await db.live_classes.find_one({"id": live_class_id})
    if not live_class:
        raise HTTPException(status_code=404, detail="Live class not found")
    
    course = await db.courses.find_one({"id": live_class['course_id']})
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    
    if not instructor or instructor['id'] != course['instructor_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.live_classes.delete_one({"id": live_class_id})
    return {"message": "Live class deleted"}


# ==================== ENROLLMENT ROUTES ====================
@api_router.post("/enrollments")
async def create_enrollment(course_id: str, current_user: User = Depends(get_current_user)):
    existing = await db.enrollments.find_one({"user_id": current_user.id, "course_id": course_id})
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled")
    
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
            result.append({**enrollment, "course": course})
    
    return result


@api_router.patch("/enrollments/{enrollment_id}/progress")
async def update_progress(enrollment_id: str, progress: float, current_user: User = Depends(get_current_user)):
    enrollment = await db.enrollments.find_one({"id": enrollment_id, "user_id": current_user.id})
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    updates = {"progress": progress}
    cert_id = None
    
    if progress >= 100:
        updates['status'] = 'completed'
        # Try to generate certificate (will check quiz requirements)
        cert_id = await generate_certificate_if_eligible(current_user.id, enrollment['course_id'])
    
    await db.enrollments.update_one({"id": enrollment_id}, {"$set": updates})
    
    return {
        "message": "Progress updated",
        "progress": progress,
        "certificate_earned": cert_id is not None,
        "certificate_id": cert_id
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
                            
                            final_price = max(0, original_price - discount_amount)
                            coupon_id = coupon['id']
    
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(
        api_key=os.environ.get('STRIPE_SECRET_KEY'),
        webhook_url=webhook_url
    )
    
    success_url = f"{host_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{host_url}/payment/cancel"
    
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
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
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
    if status.payment_status in valid_statuses and payment['payment_status'] != 'paid':
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


# ==================== AI ROUTES ====================
@api_router.post("/ai/course-assistant")
async def ai_course_assistant(prompt: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in ["instructor", "admin"]:
        raise HTTPException(status_code=403, detail="Instructor only")
    
    chat = LlmChat(
        api_key=os.environ.get('GEMINI_API_KEY'),
        session_id=f"assistant-{current_user.id}",
        system_message="You are an AI assistant helping instructors create course content. Provide helpful suggestions for course descriptions, lesson titles, and quiz questions."
    ).with_model("google", "gemini-2.5-flash")
    
    message = UserMessage(text=prompt)
    response = await chat.send_message(message)
    return {"response": response}


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
        api_key=os.environ.get('GEMINI_API_KEY'),
        session_id=f"tutor-{current_user.id}-{course_id}",
        system_message=f"You are an AI tutor for this course. Help students understand the material.\n\n{context}"
    ).with_model("google", "gemini-2.5-flash")
    
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
    
    new_status = "published" if approved else "rejected"
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"status": new_status}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"message": f"Course {new_status}"}


@api_router.patch("/admin/courses/{course_id}/feature")
async def toggle_featured_course(course_id: str, featured: bool, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"is_featured": featured}}
    )
    
    if result.modified_count == 0:
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
    
    instructor = await db.instructors.find_one({"user_id": current_user.id})
    if not instructor or instructor['id'] != course['instructor_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    quiz = Quiz(**quiz_data)
    doc = quiz.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.quizzes.insert_one(doc)
    return quiz


@api_router.get("/quizzes/{course_id}")
async def get_quizzes(course_id: str):
    quizzes = await db.quizzes.find({"course_id": course_id}, {"_id": 0}).to_list(1000)
    return quizzes


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



# Include router and add CORS
app.include_router(api_router)

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
        if instructor:
            await db.instructors.update_one(
                {"id": instructor['id']},
                {"$set": {"verification_status": "approved"}}
            )
            results.append("Instructor -> APPROVED")
        else:
            # Create instructor
            results.append("Creating Instructor Profile")
            new_instructor = {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "bio": "Auto-fixed",
                "verification_status": "approved",
                "earnings": 0.0,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.instructors.insert_one(new_instructor)
        
        return {"status": "Success", "details": results}
    except Exception as e:
        logger.error(f"Fix account failed: {e}")
        return {"status": "Error", "error": str(e)}

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
