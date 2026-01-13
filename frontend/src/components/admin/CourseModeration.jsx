import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, Star, BookOpen, Trash2, ShieldOff } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CourseModeration() {
  const [courses, setCourses] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending'); // pending, all

  useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    const token = localStorage.getItem('token');
    try {
      const [pendingRes, allCoursesRes] = await Promise.all([
        axios.get(`${API}/admin/courses/pending`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/courses`)
      ]);

      setCourses(pendingRes.data);
      setAllCourses(allCoursesRes.data);
    } catch (error) {
      toast.error('Failed to load courses');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveCourse = async (courseId) => {
    const token = localStorage.getItem('token');
    try {
      await axios.patch(`${API}/admin/courses/${courseId}/moderate`, null, {
        params: { approved: true },
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course approved and published!');
      fetchCourses();
    } catch (error) {
      toast.error('Failed to approve course');
    }
  };

  const handleRejectCourse = async (courseId) => {
    const token = localStorage.getItem('token');
    try {
      await axios.patch(`${API}/admin/courses/${courseId}/moderate`, null, {
        params: { approved: false },
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course rejected');
      fetchCourses();
    } catch (error) {
      toast.error('Failed to reject course');
    }
  };

  const handleToggleFeatured = async (courseId, currentStatus) => {
    const token = localStorage.getItem('token');
    try {
      await axios.patch(`${API}/admin/courses/${courseId}/feature`, null, {
        params: { featured: !currentStatus },
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Course ${!currentStatus ? 'featured' : 'unfeatured'} successfully`);
      fetchCourses();
    } catch (error) {
      toast.error('Failed to update featured status');
    }
  };

  const handleUnpublishCourse = async (courseId) => {
    const token = localStorage.getItem('token');
    try {
      await axios.patch(`${API}/admin/courses/${courseId}/moderate`, null, {
        params: { approved: false },
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course unpublished');
      fetchCourses();
    } catch (error) {
      toast.error('Failed to unpublish course');
    }
  };

  const handleDeleteCourse = async (courseId) => {
    if (!window.confirm('Are you certain you want to delete this course? This cannot be undone.')) return;

    const token = localStorage.getItem('token');
    try {
      await axios.delete(`${API}/courses/${courseId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course deleted forever');
      fetchCourses();
    } catch (error) {
      toast.error('Failed to delete course');
    }
  };

  const publishedCourses = allCourses.filter(c => c.status === 'published');

  if (loading) return <div className="loading">Loading courses...</div>;

  return (
    <div className="course-moderation" data-testid="course-moderation">
      <div className="moderation-header">
        <h2>Course Management</h2>
        <div className="moderation-tabs">
          <button
            className={`tab-btn ${activeTab === 'pending' ? 'active' : ''}`}
            onClick={() => setActiveTab('pending')}
            data-testid="pending-tab"
          >
            <BookOpen size={18} />
            Pending Review ({courses.length})
          </button>
          <button
            className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
            data-testid="published-tab"
          >
            <Star size={18} />
            Published Courses ({publishedCourses.length})
          </button>
        </div>
      </div>

      {activeTab === 'pending' && (
        <div className="pending-courses-section">
          {courses.length === 0 ? (
            <div className="empty-state">
              <BookOpen size={48} className="empty-icon" />
              <p>No courses pending review</p>
            </div>
          ) : (
            <div className="courses-grid">
              {courses.map((course) => (
                <div key={course.id} className="moderation-course-card" data-testid={`course-${course.id}`}>
                  <div className="course-thumbnail">
                    <img src={course.thumbnail || '/placeholder-course.png'} alt={course.title} />
                  </div>
                  <div className="course-details">
                    <h3>{course.title}</h3>
                    <p className="course-description">{course.description}</p>
                    <div className="course-meta">
                      <span className="category-tag">{course.category}</span>
                      <span className="price-tag">${course.price}</span>
                    </div>
                    <div className="instructor-info">
                      <span className="instructor-label">Instructor:</span>
                      <span className="instructor-name">{course.instructor_name}</span>
                    </div>
                  </div>
                  <div className="moderation-actions">
                    <Button
                      data-testid={`approve-${course.id}`}
                      onClick={() => handleApproveCourse(course.id)}
                      className="approve-btn"
                    >
                      <CheckCircle size={18} className="mr-2" />
                      Approve & Publish
                    </Button>
                    <Button
                      data-testid={`reject-${course.id}`}
                      onClick={() => handleRejectCourse(course.id)}
                      variant="outline"
                      className="reject-btn"
                    >
                      <XCircle size={18} className="mr-2" />
                      Reject
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'all' && (
        <div className="published-courses-section">
          <div className="courses-table-container">
            <table className="courses-table">
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Status</th>
                  <th>Featured</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {publishedCourses.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="empty-cell">No published courses</td>
                  </tr>
                ) : (
                  publishedCourses.map((course) => (
                    <tr key={course.id} data-testid={`published-course-${course.id}`}>
                      <td>
                        <div className="course-cell">
                          <img src={course.thumbnail || '/placeholder-course.png'} alt={course.title} className="table-thumbnail" />
                          <span>{course.title}</span>
                        </div>
                      </td>
                      <td>{course.category}</td>
                      <td>${course.price}</td>
                      <td>
                        <span className="status-badge published">{course.status}</span>
                      </td>
                      <td>
                        {course.is_featured ? (
                          <Star size={18} fill="#f59e0b" color="#f59e0b" />
                        ) : (
                          <Star size={18} color="#d1d5db" />
                        )}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant={course.is_featured ? "default" : "outline"}
                            onClick={() => handleToggleFeatured(course.id, course.is_featured)}
                            data-testid={`feature-${course.id}`}
                          >
                            <Star size={16} className="mr-1" />
                            {course.is_featured ? 'Unfeature' : 'Feature'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-orange-600 border-orange-200 hover:bg-orange-50"
                            onClick={() => handleUnpublishCourse(course.id)}
                            data-testid={`unpublish-${course.id}`}
                          >
                            <ShieldOff size={16} className="mr-1" />
                            Unpublish
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDeleteCourse(course.id)}
                            data-testid={`delete-${course.id}`}
                          >
                            <Trash2 size={16} className="mr-1" />
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
