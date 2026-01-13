import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import CouponManager from '@/components/CouponManager';
import UserManagement from '@/components/admin/UserManagement';
import InstructorApprovals from '@/components/admin/InstructorApprovals';
import PlatformAnalytics from '@/components/admin/PlatformAnalytics';
import CourseModeration from '@/components/admin/CourseModeration';
import { Users, UserCheck, BarChart3, Tag, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function AdminDashboard({ user, logout }) {
  const [stats, setStats] = useState({ pendingInstructors: 0, totalUsers: 0 });

  useEffect(() => {
    fetchQuickStats();
  }, []);

  const fetchQuickStats = async () => {
    const token = localStorage.getItem('token');

    // 1. Fetch Instructors (Pending count)
    let pending = 0;
    try {
      const instructorsRes = await axios.get(`${API}/instructors`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      // DEBUG: Log the raw response to see what we're getting
      console.log('=== DEBUG: Instructors API Response ===');
      console.log('Response type:', typeof instructorsRes.data);
      console.log('Is Array:', Array.isArray(instructorsRes.data));
      console.log('Raw data:', instructorsRes.data);

      // Ensure data is an array before filtering
      const instructors = Array.isArray(instructorsRes.data) ? instructorsRes.data : [];

      // DEBUG: Log filtering details
      console.log('Total instructors:', instructors.length);
      instructors.forEach((inst, idx) => {
        console.log(`Instructor ${idx}:`, {
          id: inst.id,
          user_id: inst.user_id,
          verification_status: inst.verification_status,
          status: inst.status // Check if there's a different field
        });
      });

      const pendingInstructors = instructors.filter(i => i.verification_status === 'pending');
      console.log('Pending instructors found:', pendingInstructors.length);
      pending = pendingInstructors.length;
    } catch (error) {
      console.error('Failed to load instructors:', error);
    }

    // 2. Fetch Users (Total count)
    let totalUsers = 0;
    try {
      const usersRes = await axios.get(`${API}/admin/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      totalUsers = usersRes.data.length;
    } catch (error) {
      // Endpoint might be missing currently, don't block other stats
      console.error('Failed to load users:', error);
    }

    setStats({
      pendingInstructors: pending,
      totalUsers: totalUsers
    });
  };

  return (
    <div data-testid="admin-dashboard" className="dashboard-page">
      <Navbar user={user} logout={logout} />
      <div className="dashboard-container">
        <div className="dashboard-header">
          <div>
            <h1>Admin Dashboard</h1>
            <p>Manage and monitor your learning platform</p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="admin-quick-stats" data-testid="admin-stats">
          <div className="quick-stat-card">
            <Users className="stat-icon" size={24} />
            <div>
              <h3>{stats.totalUsers}</h3>
              <p>Total Users</p>
            </div>
          </div>
          <div className="quick-stat-card pending">
            <UserCheck className="stat-icon" size={24} />
            <div>
              <h3>{stats.pendingInstructors}</h3>
              <p>Pending Approvals</p>
            </div>
          </div>
        </div>

        <Tabs defaultValue="analytics" className="dashboard-tabs">
          <TabsList>
            <TabsTrigger value="analytics" data-testid="analytics-tab">
              <BarChart3 size={18} className="mr-2" />
              Analytics
            </TabsTrigger>
            <TabsTrigger value="courses" data-testid="courses-tab">
              <BookOpen size={18} className="mr-2" />
              Courses
            </TabsTrigger>
            <TabsTrigger value="instructors" data-testid="instructors-tab">
              <UserCheck size={18} className="mr-2" />
              Instructors {stats.pendingInstructors > 0 && `(${stats.pendingInstructors})`}
            </TabsTrigger>
            <TabsTrigger value="users" data-testid="users-tab">
              <Users size={18} className="mr-2" />
              Users
            </TabsTrigger>
            <TabsTrigger value="coupons" data-testid="coupons-tab">
              <Tag size={18} className="mr-2" />
              Coupons
            </TabsTrigger>
          </TabsList>

          <TabsContent value="analytics">
            <PlatformAnalytics />
          </TabsContent>

          <TabsContent value="courses">
            <div className="flex justify-end mb-4">
              <Button onClick={() => window.open('/dashboard/instructor', '_blank')}>
                <BookOpen size={18} className="mr-2" />
                Manage Courses (Instructor View)
              </Button>
            </div>
            <CourseModeration />
          </TabsContent>

          <TabsContent value="instructors">
            <InstructorApprovals />
          </TabsContent>

          <TabsContent value="users">
            <UserManagement />
          </TabsContent>

          <TabsContent value="coupons">
            <CouponManager />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}