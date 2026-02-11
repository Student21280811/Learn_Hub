# 🚀 LearnHub - Complete Guide to Run the Project

## 📋 Prerequisites

Install these before starting:

| Software | Version | Download |
|----------|---------|----------|
| **Python** | 3.9+ | https://www.python.org/downloads/ |
| **Node.js** | 18+ | https://nodejs.org/ |
| **npm** | 9+ | Comes with Node.js |
| **Git** | Latest | https://git-scm.com/ |

### Required Accounts (for full features)

| Service | Purpose | Get Keys From |
|---------|---------|---------------|
| **MongoDB Atlas** | Database | https://www.mongodb.com/cloud/atlas |
| **Stripe** | Payments | https://dashboard.stripe.com/test/apikeys |
| **SendGrid** | Emails | https://sendgrid.com |
| **Groq** | AI Features | https://console.groq.com |

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Ali-Hamas/Learn_Hub.git
cd Learn_Hub
```

### Step 2: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Configure Backend Environment

Open `backend/.env` and update these values:

```env
# Database (MongoDB Atlas connection string)
MONGO_URL=mongodb+srv://your_user:your_password@cluster.mongodb.net/learnhub?retryWrites=true&w=majority
DB_NAME=learnhub

# JWT Secret (change this for security)
JWT_SECRET=your-super-secret-key-change-this-in-production

# Admin Commission
ADMIN_COMMISSION=0.15

# Stripe (Payments) - https://dashboard.stripe.com/test/apikeys
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET
STRIPE_CLIENT_ID=ca_YOUR_CLIENT_ID_HERE

# SendGrid (Emails) - https://sendgrid.com
SENDGRID_API_KEY=SG.YOUR_API_KEY_HERE
SENDER_EMAIL=your-verified-email@example.com

# AI Features - https://console.groq.com
GROQ_API_KEY=gsk_YOUR_GROQ_KEY_HERE
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY

# Server Config
HOST=0.0.0.0
PORT=8001
FRONTEND_URL=http://localhost:3000
```

### Step 4: Start Backend Server

```bash
# Make sure you're in the backend folder with venv activated
cd backend
uvicorn server:app --reload --port 8001
```

✅ Backend should now be running at: **http://localhost:8001**
📄 API Docs available at: **http://localhost:8001/docs**

### Step 5: Frontend Setup (New Terminal)

```bash
# Open a NEW terminal window
cd frontend

# Install dependencies
npm install

# Note: If you get dependency errors, try:
npm install --legacy-peer-deps
```

### Step 6: Configure Frontend Environment

Open `frontend/.env` and set for **local development**:

```env
REACT_APP_API_URL=http://localhost:8001
REACT_APP_BASE_URL=http://localhost:8001
REACT_APP_BACKEND_URL=http://localhost:8001
```

> ⚠️ **Important**: For local development, use `http://localhost:8001`. For production, use your actual backend URL.

### Step 7: Start Frontend

```bash
npm start
```

✅ Frontend should now be running at: **http://localhost:3000**

---

## 🖥️ Access Points

| Service | URL |
|---------|-----|
| **Frontend (Website)** | http://localhost:3000 |
| **Backend API** | http://localhost:8001/api |
| **API Documentation** | http://localhost:8001/docs |

---

## 👤 User Roles & Getting Started

### Creating Your First Account

1. Go to **http://localhost:3000**
2. Click **Register** and create a new account
3. Default role is **Student**

### Promoting to Admin

To make yourself an admin:

1. Open **MongoDB Atlas Dashboard** → Collections → `users` collection
2. Find your user document
3. Change `"role": "student"` to `"role": "admin"`
4. Refresh the website and you'll have admin access

### Role Capabilities

| Role | What They Can Do |
|------|-----------------|
| **Student** | Browse courses, enroll, take quizzes, get certificates |
| **Instructor** | Create/manage courses, upload lessons, view earnings |
| **Admin** | Approve instructors, manage all users, moderate content |

---

## 🔧 Troubleshooting

### ❌ Backend won't start

**Error**: `ModuleNotFoundError: No module named 'xyz'`
```bash
pip install -r requirements.txt
```

**Error**: `MongoDB connection failed`
- Check your `MONGO_URL` in `.env`
- Whitelist your IP in MongoDB Atlas → Network Access → Add IP → Allow Access from Anywhere (0.0.0.0/0)

### ❌ Frontend won't start

**Error**: `npm ERR! code ERESOLVE`
```bash
# Delete node_modules and reinstall
Remove-Item -Recurse -Force node_modules   # Windows
# rm -rf node_modules                      # macOS/Linux
npm install --legacy-peer-deps
```

### ❌ Port already in use

**Error**: `Port 8001 is already in use`
```bash
# Windows - Find and kill process
netstat -ano | findstr :8001
taskkill /PID <PID_NUMBER> /F

# macOS/Linux
lsof -i :8001
kill -9 <PID_NUMBER>
```

### ❌ CORS error in browser

Make sure `FRONTEND_URL` in `backend/.env` matches your frontend URL:
```env
FRONTEND_URL=http://localhost:3000
```

### ❌ Stripe "Connect" button not working

Get your actual Stripe Client ID:
1. Go to https://dashboard.stripe.com/settings/applications
2. Toggle **Test mode** (top right)
3. Copy your **Client ID** (starts with `ca_...`)
4. Update `STRIPE_CLIENT_ID` in `backend/.env`
5. Restart backend

---

## 🌐 Production Deployment

### For Vercel (Frontend)

1. Update `frontend/.env`:
   ```env
   REACT_APP_BACKEND_URL=https://your-backend-url.com
   ```

2. Build:
   ```bash
   cd frontend
   npm run build
   ```

3. Deploy the `build` folder to Vercel, or connect your GitHub repo directly.

### For Render / Railway (Backend)

1. Push your code to GitHub
2. Connect your repo to Render/Railway
3. Set environment variables in the dashboard
4. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`

---

## 📁 Project Structure

```
Learn_Hub/
├── backend/
│   ├── server.py           # Main FastAPI application (all routes)
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # Backend environment variables
│   └── uploads/            # Uploaded files (thumbnails, PDFs)
│
├── frontend/
│   ├── src/
│   │   ├── pages/          # Page components (Landing, Catalog, etc.)
│   │   ├── components/     # Reusable UI components
│   │   └── App.jsx         # Main React app with routes
│   ├── public/             # Static assets
│   ├── package.json        # Node.js dependencies
│   └── .env                # Frontend environment variables
│
├── SETUP_GUIDE.md          # Detailed setup guide
├── DEPLOYMENT_GUIDE.md     # Production deployment guide
└── README.md               # Project overview
```

---

## 🔁 Daily Development Workflow

Every time you want to work on the project:

```bash
# Terminal 1 - Start Backend
cd backend
.\venv\Scripts\activate     # Windows
uvicorn server:app --reload --port 8001

# Terminal 2 - Start Frontend
cd frontend
npm start
```

---

**Happy Coding! 🎓**
