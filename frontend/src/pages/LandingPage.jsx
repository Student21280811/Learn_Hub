import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { BookOpen, Users, Award, TrendingUp } from 'lucide-react';
import Navbar from '@/components/Navbar';
import BlogSection from '@/components/BlogSection';
import NewsletterSignup from '@/components/NewsletterSignup';
import '@/components/Newsletter.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function LandingPage({ user, logout }) {
  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState({ courses: 0, students: 0 });
  const navigate = useNavigate();

  useEffect(() => {
    fetchFeaturedCourses();
  }, []);

  const fetchFeaturedCourses = async () => {
    try {
      const response = await axios.get(`${API}/courses?status=published`);
      setCourses(response.data.slice(0, 6));
      setStats({ courses: response.data.length, students: response.data.length * 15 });
    } catch (error) {
      console.error('Error fetching courses:', error);
    }
  };

  return (
    <div className="landing-page">
      <Navbar user={user} logout={logout} />

      {/* Hero Section */}
      <section className="hero-section" data-testid="hero-section">
        <div className="hero-content">
          <h1 className="hero-title" data-testid="hero-title">
            Learn Without Limits
          </h1>
          <p className="hero-subtitle" data-testid="hero-subtitle">
            Join thousands of learners mastering new skills with world-class instructors
          </p>
          <div className="hero-actions">
            <Button
              data-testid="explore-courses-btn"
              onClick={() => navigate('/courses')}
              className="btn-primary"
              size="lg"
            >
              Explore Courses
            </Button>
            {!user && (
              <Button
                data-testid="get-started-btn"
                onClick={() => navigate('/register')}
                variant="outline"
                size="lg"
                className="btn-outline"
              >
                Get Started Free
              </Button>
            )}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats-section" data-testid="stats-section">
        <div className="stats-container">
          <div className="stat-card" data-testid="stat-courses">
            <BookOpen className="stat-icon" />
            <h3>{stats.courses}+</h3>
            <p>Courses Available</p>
          </div>
          <div className="stat-card" data-testid="stat-students">
            <Users className="stat-icon" />
            <h3>{stats.students}+</h3>
            <p>Active Students</p>
          </div>
          <div className="stat-card" data-testid="stat-instructors">
            <Award className="stat-icon" />
            <h3>50+</h3>
            <p>Expert Instructors</p>
          </div>
          <div className="stat-card" data-testid="stat-completion">
            <TrendingUp className="stat-icon" />
            <h3>95%</h3>
            <p>Completion Rate</p>
          </div>
        </div>
      </section>

      {/* Featured Courses */}
      <section className="featured-section" data-testid="featured-courses">
        <h2 className="section-title">Featured Courses</h2>
        <div className="courses-grid">
          {courses.map((course) => (
            <div key={course.id} className="course-card" data-testid={`course-card-${course.id}`}>
              <div className="course-thumbnail">
                <img src={course.thumbnail || '/placeholder-course.png'} alt={course.title} />
              </div>
              <div className="course-content">
                <span className="course-category">{course.category}</span>
                <h3 className="course-title">{course.title}</h3>
                <p className="course-description">{course.description.substring(0, 100)}...</p>
                <div className="course-footer">
                  <span className="course-price">${course.price}</span>
                  <Button
                    data-testid={`view-course-${course.id}`}
                    onClick={() => navigate(`/course/${course.id}`)}
                    size="sm"
                  >
                    View Course
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Blog Section */}
      <BlogSection />

      {/* CTA Section */}
      <section className="cta-section" data-testid="cta-section">
        <div className="cta-container">
          <div className="cta-content">
            <h2>Start Learning Today</h2>
            <p>Access courses from top instructors and boost your career</p>
            <Button
              data-testid="browse-courses-btn"
              onClick={() => navigate('/courses')}
              size="lg"
              className="btn-primary"
            >
              Browse All Courses
            </Button>
          </div>

          <div className="cta-newsletter">
            <NewsletterSignup />
          </div>
        </div>
      </section>
    </div>
  );
}