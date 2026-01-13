import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { BookOpen, User, LogOut } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export default function Navbar({ user, logout }) {
  const navigate = useNavigate();

  const getDashboardLink = () => {
    if (!user) return '/login';
    if (user.role === 'admin') return '/dashboard/admin';
    if (user.role === 'instructor') return '/dashboard/instructor';
    return '/dashboard/student';
  };

  return (
    <nav className="navbar" data-testid="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand" data-testid="navbar-brand">
          <BookOpen className="brand-icon" />
          <span>LearnHub</span>
        </Link>

        <div className="navbar-links">
          <Link to="/" data-testid="nav-home">Home</Link>
          <Link to="/courses" data-testid="nav-courses">Courses</Link>
          {user && <Link to="/profile" data-testid="nav-my-profile">Profile</Link>}
        </div>

        <div className="navbar-actions">
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" data-testid="user-menu">
                  <User size={20} />
                  <span>{user.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  data-testid="nav-dashboard"
                  onClick={() => navigate(getDashboardLink())}
                >
                  Dashboard
                </DropdownMenuItem>
                <DropdownMenuItem
                  data-testid="nav-profile"
                  onClick={() => navigate('/profile')}
                >
                  Profile
                </DropdownMenuItem>
                <DropdownMenuItem
                  data-testid="nav-logout"
                  onClick={() => {
                    logout();
                    navigate('/');
                  }}
                >
                  <LogOut size={16} className="mr-2" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Button
                data-testid="nav-login-btn"
                variant="ghost"
                onClick={() => navigate('/login')}
              >
                Login
              </Button>
              <Button
                data-testid="nav-register-btn"
                onClick={() => navigate('/register')}
              >
                Sign Up
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}