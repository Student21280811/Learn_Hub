import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Navbar from '@/components/Navbar';
import CreateCourseForm from '@/components/instructor/CreateCourseForm';
import CoursesList from '@/components/instructor/CoursesList';
import EarningsView from '@/components/instructor/EarningsView';
import StripeConnectCard from '@/components/instructor/StripeConnectCard';
import { Plus, BookOpen, DollarSign, Users, Clock, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function InstructorDashboard({ user, logout }) {
  const [instructor, setInstructor] = useState(null);
  const [courses, setCourses] = useState([]);
  const [stats, setStats] = useState({ courses: 0, students: 0, earnings: 0 });
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    // Check for Stripe connection callback
    const stripeConnected = searchParams.get('stripe_connected');
    const stripeError = searchParams.get('stripe_error');

    if (stripeConnected === 'true') {
      toast.success('Stripe account connected successfully! You\'ll receive 90% of course sales.');
      // Clean URL
      window.history.replaceState({}, '', '/dashboard/instructor');
    } else if (stripeError === 'true') {
      toast.error('Failed to connect Stripe account. Please try again.');
      window.history.replaceState({}, '', '/dashboard/instructor');
    }
  }, [searchParams]);

  useEffect(() => {
    if (user) {
      fetchInstructorData();
    }
  }, [user]);

  const fetchInstructorData = async () => {
    try {
      let activeInstructor = null;
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      // 1. Get/Set Instructor Profile
      const instructorsRes = await axios.get(`${API}/instructors`, { headers });
      activeInstructor = instructorsRes.data.find(i => i.user_id === user.id);

      if (user?.role === 'admin') {
        if (!activeInstructor) {
          // Virtual instructor for admin if no record exists
          activeInstructor = { id: `admin-inst-${user.id}`, verification_status: 'approved', earnings: 0 };
        }
      } else {
        // Regular instructor
        if (!activeInstructor) {
          // If no instructor record exists, prompt them to apply or handle gracefully
          console.warn("No instructor profile found for user:", user.id);
          setLoading(false);
          return;
        }
      }

      setInstructor(activeInstructor);

      // 2. Fetch Courses for this instructor (any status)
      const coursesRes = await axios.get(`${API}/courses?instructor_id=${activeInstructor.id}&status=all&token=${token}`, { headers });
      const myCourses = coursesRes.data;
      setCourses(myCourses);

      // 3. Calculate Stats
      const publishedCourses = myCourses.filter(c => c.status === 'published');
      setStats({
        courses: myCourses.length, // Total courses (published + drafts)
        published: publishedCourses.length,
        students: 0, // TODO: Implement student count from enrollments
        earnings: activeInstructor.earnings || 0
      });

    } catch (error) {
      console.error('Failed to load instructor dashboard data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleCourseCreated = () => {
    setShowCreateForm(false);
    fetchInstructorData();
  };

  if (loading) return <div className="loading">Loading...</div>;

  if (user?.role !== 'admin' && (!instructor || instructor.verification_status === 'pending')) {
    return (
      <div data-testid="instructor-dashboard" className="dashboard-page">
        <Navbar user={user} logout={logout} />
        <div className="dashboard-container">
          <div className="pending-status-card" data-testid="pending-approval">
            <Clock size={80} className="status-large-icon pending-icon" />
            <h1>Application Under Review</h1>
            <p>Your instructor account is currently being verified by our administrators. This usually takes 24-48 hours.</p>
            <div className="pending-actions">
              <Button onClick={() => navigate('/dashboard/student')}>
                Switch to Student Dashboard
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (user?.role !== 'admin' && instructor.verification_status === 'rejected') {
    return (
      <div data-testid="instructor-dashboard" className="dashboard-page">
        <Navbar user={user} logout={logout} />
        <div className="dashboard-container">
          <div className="pending-status-card rejected" data-testid="status-rejected">
            <AlertCircle size={80} className="status-large-icon rejected-icon" />
            <h1>Application Not Approved</h1>
            <p>Unfortunately, we couldn't approve your instructor profile at this time.</p>
            <div className="pending-actions">
              <Button onClick={() => navigate('/dashboard/student')}>
                Return to Student Dashboard
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="instructor-dashboard" className="dashboard-page">
      <Navbar user={user} logout={logout} />

      <div className="dashboard-container">
        <div className="dashboard-header">
          <div>
            <h1 data-testid="dashboard-title">Instructor Dashboard</h1>
            <p>Manage your courses and track earnings</p>
          </div>
          <Button
            data-testid="create-course-btn"
            onClick={() => setShowCreateForm(true)}
          >
            <Plus size={18} className="mr-2" />
            Create Course
          </Button>
        </div>

        {/* Stats */}
        <div className="dashboard-stats" data-testid="instructor-stats">
          <div className="stat-card">
            <BookOpen className="stat-icon" />
            <div>
              <h3 data-testid="courses-count">{stats.courses}</h3>
              <p>Total Courses</p>
            </div>
          </div>
          <div className="stat-card">
            <Users className="stat-icon" />
            <div>
              <h3 data-testid="students-count">{stats.students}</h3>
              <p>Total Students</p>
            </div>
          </div>
          <div className="stat-card">
            <DollarSign className="stat-icon" />
            <div>
              <h3 data-testid="earnings-amount">${stats.earnings.toFixed(2)}</h3>
              <p>Total Earnings</p>
            </div>
          </div>
        </div>

        {/* Course Management Tabs */}
        <Tabs defaultValue="courses" className="dashboard-tabs">
          <TabsList>
            <TabsTrigger value="courses" data-testid="courses-tab">My Courses</TabsTrigger>
            <TabsTrigger value="earnings" data-testid="earnings-tab">Earnings</TabsTrigger>
          </TabsList>

          <TabsContent value="courses">
            <CoursesList
              courses={courses}
              instructorId={instructor.id}
              onRefresh={fetchInstructorData}
            />
          </TabsContent>

          <TabsContent value="earnings">
            <StripeConnectCard />
            <EarningsView
              instructorId={instructor.id}
              totalEarnings={stats.earnings}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Create Course Modal/Form */}
      {showCreateForm && (
        <CreateCourseForm
          onClose={() => setShowCreateForm(false)}
          onSuccess={handleCourseCreated}
        />
      )}
    </div>
  );
}