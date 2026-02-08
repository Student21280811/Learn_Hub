# 🚀 How to Run LearnHub by BritSyncAI Academy

This guide provides steps to run your application locally for development and how to manage your live deployment (Fasthosts + Render).

---

## 💻 Local Development

Follow these steps to run the app on your own computer.

### 1. Prerequisites
- **Python 3.11+** installed
- **Node.js & pnpm** installed
- **MongoDB** (local installation or MongoDB Atlas)

### 2. Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure `.env`:
   - Open `backend/.env`
   - Ensure `MONGO_URL` is correct.
5. Start the server:
   ```bash
   uvicorn server:app --reload --port 8001
   ```

### 3. Frontend Setup
1. Open a new terminal and navigate to the frontend:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. Configure `.env`:
   - Set `REACT_APP_BACKEND_URL=http://localhost:8001` for local testing.
4. Start the development server:
   ```bash
   pnpm start
   ```

---

## 🌐 Production Running Guide

Your setup is hybrid: **Frontend on Fasthosts** and **Backend on Render**.

### 1. Backend (on Render)
- Every time you push code to GitHub, Render will automatically re-deploy your backend.
- **IMPORTANT**: Ensure the `MONGO_URL` environment variable is set in the **Render Dashboard -> Settings -> Environment Variables**. This is where your live database password goes.

### 2. Frontend (on Fasthosts)
Whenever you make changes to the frontend:
1. Navigate to `frontend`.
2. Ensure `frontend/.env` has:
   ```
   REACT_APP_BACKEND_URL=https://learnhub-backend-y5fz.onrender.com
   ```
3. Build the production files:
   ```bash
   pnpm run build
   ```
4. **Upload**: Use FTP/SFTP to upload the contents of the `frontend/build` folder to your Fasthosts server directory (usually `public_html`).

---

## 🛠️ Common Tasks

### Creating an Admin
To create the first admin user:
1. Register a normal account on the website.
2. Go to your MongoDB Atlas dashboard.
3. Find the user in the `users` collection.
4. Update their `role` field from `"student"` to `"admin"`.

### Updating Branding
1. Change values in `frontend/public/index.html`.
2. Re-build and re-upload the frontend.

---

**BritSyncAI Academy** - *Empowering Education with AI*
