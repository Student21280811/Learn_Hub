import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import Navbar from '@/components/Navbar';
import CourseReviews from '@/components/student/CourseReviews';
import { BookOpen, Clock, Award, Tag, Check } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CourseDetail({ user, logout }) {
  const { id } = useParams();
  const [course, setCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [enrolling, setEnrolling] = useState(false);
  const [isEnrolled, setIsEnrolled] = useState(false);
  const [couponCode, setCouponCode] = useState('');
  const [validatingCoupon, setValidatingCoupon] = useState(false);
  const [appliedCoupon, setAppliedCoupon] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCourse();
    if (user) checkEnrollment();
  }, [id, user]);

  const fetchCourse = async () => {
    try {
      const [courseRes, lessonsRes] = await Promise.all([
        axios.get(`${API}/courses/${id}`),
        axios.get(`${API}/courses/${id}/lessons`)
      ]);
      setCourse(courseRes.data);
      setLessons(lessonsRes.data);
    } catch (error) {
      toast.error('Failed to load course');
    } finally {
      setLoading(false);
    }
  };

  const checkEnrollment = async () => {
    try {
      const response = await axios.get(`${API}/enrollments/my-courses`);
      const enrolled = response.data.some(e => e.course_id === id);
      setIsEnrolled(enrolled);
    } catch (error) {
      console.error('Error checking enrollment:', error);
    }
  };

  const validateCoupon = async () => {
    if (!couponCode.trim()) {
      toast.error('Please enter a coupon code');
      return;
    }

    if (!user) {
      toast.error('Please login to apply coupon');
      return;
    }

    setValidatingCoupon(true);
    try {
      const response = await axios.post(`${API}/coupons/validate?code=${couponCode}&course_id=${id}`);
      setAppliedCoupon(response.data);
      toast.success('Coupon applied successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Invalid coupon code');
      setAppliedCoupon(null);
    } finally {
      setValidatingCoupon(false);
    }
  };

  const removeCoupon = () => {
    setCouponCode('');
    setAppliedCoupon(null);
    toast.info('Coupon removed');
  };

  const handleEnroll = async () => {
    if (!user) {
      toast.error('Please login to enroll');
      navigate('/login');
      return;
    }

    setEnrolling(true);
    try {
      const url = appliedCoupon
        ? `${API}/payments/checkout?course_id=${id}&coupon_code=${couponCode}`
        : `${API}/payments/checkout?course_id=${id}`;

      const response = await axios.post(url);
      window.location.href = response.data.url;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start checkout');
      setEnrolling(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (!course) return <div>Course not found</div>;

  return (
    <div className="course-detail-page" data-testid="course-detail">
      <Navbar user={user} logout={logout} />

      <div className="course-detail-container">
        <div className="course-hero">
          <div className="course-hero-content">
            <span className="course-category" data-testid="course-category">{course.category}</span>
            <h1 data-testid="course-title">{course.title}</h1>
            <p className="course-description" data-testid="course-description">{course.description}</p>

            <div className="course-meta">
              <div className="meta-item">
                <BookOpen size={20} />
                <span data-testid="lessons-count">{lessons.length} Lessons</span>
              </div>
              <div className="meta-item">
                <Clock size={20} />
                <span>Self-paced</span>
              </div>
              {course.instructor && (
                <div className="meta-item">
                  <Award size={20} />
                  <Link
                    to={`/profile/${course.instructor.id}`}
                    className="hover:text-primary transition-colors cursor-pointer"
                    data-testid="instructor-name"
                  >
                    {course.instructor.name}
                  </Link>
                </div>
              )}
            </div>

            {isEnrolled ? (
              <div className="course-actions">
                <Button
                  data-testid="start-learning-btn"
                  onClick={() => navigate(`/course/${id}/learn`)}
                  size="lg"
                >
                  Start Learning
                </Button>
              </div>
            ) : (
              <div className="course-pricing-section">
                {/* Coupon Input */}
                {!appliedCoupon && (
                  <div className="coupon-input-section" data-testid="coupon-section">
                    <div className="coupon-input-wrapper">
                      <Tag className="coupon-icon" size={18} />
                      <Input
                        data-testid="coupon-input"
                        type="text"
                        placeholder="Have a coupon code?"
                        value={couponCode}
                        onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                        className="coupon-input"
                        disabled={validatingCoupon}
                      />
                      <Button
                        data-testid="apply-coupon-btn"
                        onClick={validateCoupon}
                        disabled={validatingCoupon || !couponCode.trim()}
                        size="sm"
                      >
                        {validatingCoupon ? 'Validating...' : 'Apply'}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Applied Coupon Display */}
                {appliedCoupon && (
                  <div className="applied-coupon" data-testid="applied-coupon">
                    <div className="coupon-success">
                      <Check className="coupon-check-icon" size={18} />
                      <span>Coupon "{couponCode}" applied!</span>
                      <button
                        data-testid="remove-coupon-btn"
                        onClick={removeCoupon}
                        className="remove-coupon-link"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                )}

                {/* Price Display */}
                <div className="price-section">
                  {appliedCoupon ? (
                    <div className="price-with-discount">
                      <div className="original-price" data-testid="original-price">
                        <span className="strikethrough">${appliedCoupon.original_price}</span>
                      </div>
                      <div className="discount-info">
                        <span className="discount-badge">
                          {appliedCoupon.coupon.discount_type === 'percentage'
                            ? `${appliedCoupon.coupon.discount_value}% OFF`
                            : `$${appliedCoupon.coupon.discount_value} OFF`}
                        </span>
                      </div>
                      <div className="final-price" data-testid="final-price">
                        <span className="price">${appliedCoupon.final_price.toFixed(2)}</span>
                      </div>
                      <div className="savings-text">
                        You save ${appliedCoupon.discount_amount.toFixed(2)}!
                      </div>
                    </div>
                  ) : (
                    <div className="price-tag" data-testid="course-price">
                      <span className="price">${course.price}</span>
                    </div>
                  )}
                </div>

                {/* Enroll Button */}
                <Button
                  data-testid="enroll-btn"
                  onClick={handleEnroll}
                  size="lg"
                  disabled={enrolling}
                  className="enroll-button"
                >
                  {enrolling ? 'Processing...' : 'Enroll Now'}
                </Button>
              </div>
            )}
          </div>

          <div className="course-thumbnail-large">
            <img src={course.thumbnail || '/placeholder-course.png'} alt={course.title} />
          </div>
        </div>

        {/* Course Content */}
        <div className="course-content-section">
          <h2>Course Content</h2>
          <div className="lessons-list" data-testid="lessons-list">
            {lessons.length === 0 ? (
              <p>No lessons available yet</p>
            ) : (
              lessons.map((lesson, index) => (
                <div key={lesson.id} className="lesson-item" data-testid={`lesson-${lesson.id}`}>
                  <div className="lesson-number">{index + 1}</div>
                  <div className="lesson-info">
                    <h4>{lesson.title}</h4>
                    <span className="lesson-type">{lesson.type}</span>
                  </div>
                  {lesson.duration && (
                    <span className="lesson-duration">{lesson.duration} min</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Reviews Section */}
        <div className="reviews-section">
          <h2>Student Reviews</h2>
          <CourseReviews
            courseId={id}
            isEnrolled={isEnrolled}
            userId={user?.id}
          />
        </div>
      </div>
    </div>
  );
}