# LearnHub - Complete Setup & Running Guide

A comprehensive online learning platform with course management, payments, and AI-powered features.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Environment Variables](#environment-variables)
6. [Running the Application](#running-the-application)
7. [Default Accounts](#default-accounts)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before running this application, ensure you have the following installed:

| Software | Version | Download Link |
|----------|---------|---------------|
| **Python** | 3.9+ | https://www.python.org/downloads/ |
| **Node.js** | 18+ | https://nodejs.org/ |
| **npm** | 9+ | Comes with Node.js |
| **Git** | Latest | https://git-scm.com/ |

### Required Accounts (for full functionality)

| Service | Purpose | Signup Link |
|---------|---------|-------------|
| **MongoDB Atlas** | Database | https://www.mongodb.com/cloud/atlas |
| **Stripe** | Payments | https://dashboard.stripe.com/register |
| **SendGrid** | Emails | https://sendgrid.com/ |
| **Groq** | AI Features | https://console.groq.com/ |

---

## Project Structure

```
VPS-Error-main/
├── backend/
│   ├── server.py          # Main FastAPI application
│   ├── requirements.txt   # Python dependencies
│   ├── .env               # Environment variables
│   └── uploads/           # Uploaded files storage
│
├── frontend/
│   ├── src/               # React source code
│   ├── public/            # Static assets
│   ├── package.json       # Node dependencies
│   └── .env               # Frontend environment variables
│
└── README.md
```

---

## Backend Setup

### Step 1: Navigate to Backend Directory

```bash
cd backend
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

1. Open `backend/.env` file
2. Fill in ALL required values (see [Environment Variables](#environment-variables) section)

---

## Frontend Setup

### Step 1: Navigate to Frontend Directory

```bash
cd frontend
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Configure Environment Variables

1. Open or create `frontend/.env` file
2. Add the following:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

> **Note:** For production, change this to your actual backend URL.

---

## Environment Variables

### Backend (`backend/.env`)

```env
# ==================== DATABASE ====================
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/learnhub?retryWrites=true&w=majority
DB_NAME=learnhub

# ==================== AUTHENTICATION ====================
JWT_SECRET=your-super-secret-key-change-this-in-production

# ==================== PLATFORM SETTINGS ====================
ADMIN_COMMISSION=0.15

# ==================== STRIPE (Payments) ====================
# Get from: https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET

# For Stripe Connect (Instructor Payouts)
# Get from: https://dashboard.stripe.com/settings/applications
STRIPE_CLIENT_ID=ca_YOUR_CLIENT_ID_HERE

# ==================== SENDGRID (Emails) ====================
# Get from: https://sendgrid.com/
SENDGRID_API_KEY=SG.YOUR_API_KEY_HERE
SENDER_EMAIL=your-verified-email@example.com

# ==================== AI FEATURES ====================
# Get from: https://console.groq.com/
GROQ_API_KEY=gsk_YOUR_GROQ_KEY_HERE

# Optional: Google AI
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY

# ==================== SERVER CONFIG ====================
HOST=0.0.0.0
PORT=8001
FRONTEND_URL=http://localhost:3000
```

### Frontend (`frontend/.env`)

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## Running the Application

### Option 1: Development Mode (Recommended for Testing)

**Terminal 1 - Backend:**
```bash
cd backend
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

uvicorn server:app --reload --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

### Option 2: Using Specific Ports

**Backend (default: 8001):**
```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Frontend (default: 3000):**
```bash
npm start
```

### Access Points

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8001/api |
| **API Docs** | http://localhost:8001/docs |

---

## Default Accounts

After starting the application, you can register new accounts or use these default roles:

| Role | Capabilities |
|------|-------------|
| **Student** | Browse courses, enroll, take quizzes, get certificates |
| **Instructor** | Create courses, manage content, view earnings |
| **Admin** | Approve instructors, moderate courses, manage users |

> **Note:** The first user to register can be promoted to admin via the database.

---

## Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error
```
Error: DNS resolution failed
```
**Solution:** 
- Check your `MONGO_URL` in `.env`
- Ensure your IP is whitelisted in MongoDB Atlas
- Try using standard connection string instead of `mongodb+srv://`

#### 2. Module Not Found (Backend)
```
ModuleNotFoundError: No module named 'xyz'
```
**Solution:**
```bash
pip install -r requirements.txt
```

#### 3. npm Errors (Frontend)
```
npm ERR! code ERESOLVE
```
**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
```

#### 4. Port Already in Use
```
Error: Port 8001 is already in use
```
**Solution:**
```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :8001
kill -9 <PID>
```

#### 5. Stripe Errors
```
No application matches the supplied client identifier
```
**Solution:** Get your actual Stripe Client ID from https://dashboard.stripe.com/settings/applications

---

## Production Deployment

For production deployment, you'll need:

1. **Use production environment variables**
2. **Build the frontend:**
   ```bash
   cd frontend
   npm run build
   ```
3. **Use a process manager for backend (e.g., PM2, Supervisor)**
4. **Set up NGINX as reverse proxy**
5. **Configure SSL certificates**
6. **Use production Stripe keys (not test keys)**

---

## Quick Start Summary

```bash
# 1. Clone the repository
git clone https://github.com/Ali-Hamas/Learn_Hub.git
cd Learn_Hub

# 2. Backend setup
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
# Edit .env with your credentials

# 3. Start backend
uvicorn server:app --reload --port 8001

# 4. Frontend setup (new terminal)
cd frontend
npm install
# Edit .env if needed

# 5. Start frontend
npm start

# 6. Open browser
# http://localhost:3000
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/Ali-Hamas/Learn_Hub/issues
- Check the troubleshooting section above

---

**Happy Learning! 🎓**
