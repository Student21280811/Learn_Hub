import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";

// Pages
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import StudentDashboard from "@/pages/StudentDashboard";
import InstructorDashboard from "@/pages/InstructorDashboard";
import AdminDashboard from "@/pages/AdminDashboard";
import CourseCatalog from "@/pages/CourseCatalog";
import CourseDetail from "@/pages/CourseDetail";
import CoursePlayer from "@/pages/CoursePlayer";
import ProfilePage from "@/pages/ProfilePage";
import PaymentSuccess from "@/pages/PaymentSuccess";
import PaymentCancel from "@/pages/PaymentCancel";
import ManageCourse from "@/pages/ManageCourse";
import BecomeInstructor from "@/pages/BecomeInstructor";
import PublicProfile from "@/pages/PublicProfile";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios interceptor for auth
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const token = localStorage.getItem("token");
  const userStr = localStorage.getItem("user");

  if (!token) {
    return <Navigate to="/login" />;
  }

  if (allowedRoles.length > 0 && userStr) {
    const user = JSON.parse(userStr);
    if (!allowedRoles.includes(user.role)) {
      return <Navigate to="/" />;
    }
  }

  return children;
};

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      setUser(JSON.parse(userStr));
    }
  }, []);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
    toast.success("Logged out successfully");
  };

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage user={user} logout={logout} />} />
          <Route path="/login" element={<LoginPage setUser={setUser} />} />
          <Route path="/register" element={<RegisterPage setUser={setUser} />} />
          <Route path="/courses" element={<CourseCatalog user={user} logout={logout} />} />
          <Route path="/course/:id" element={<CourseDetail user={user} logout={logout} />} />

          <Route
            path="/dashboard/student"
            element={
              <ProtectedRoute allowedRoles={["student"]}>
                <StudentDashboard user={user} logout={logout} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/dashboard/instructor"
            element={
              <ProtectedRoute allowedRoles={["student", "instructor", "admin"]}>
                <InstructorDashboard user={user} logout={logout} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/dashboard/admin"
            element={
              <ProtectedRoute allowedRoles={["admin"]}>
                <AdminDashboard user={user} logout={logout} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/course/:id/learn"
            element={
              <ProtectedRoute>
                <CoursePlayer user={user} logout={logout} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage user={user} logout={logout} />
              </ProtectedRoute>
            }
          />

          <Route path="/profile/:id" element={<PublicProfile user={user} logout={logout} />} />

          <Route path="/payment/success" element={<PaymentSuccess user={user} logout={logout} />} />
          <Route path="/payment/cancel" element={<PaymentCancel user={user} logout={logout} />} />

          <Route path="/become-instructor" element={<BecomeInstructor user={user} logout={logout} />} />

          <Route
            path="/instructor/course/:id"
            element={
              <ProtectedRoute allowedRoles={["instructor", "admin"]}>
                <ManageCourse user={user} logout={logout} />
              </ProtectedRoute>
            }
          />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
