import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import Navbar from '@/components/Navbar';
import { Search } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const categories = ['Programming', 'Design', 'Business', 'Marketing', 'Photography', 'Music', 'Health', 'Language'];

export default function CourseCatalog({ user, logout }) {
  const [courses, setCourses] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCourses();
  }, []);

  const filteredCourses = React.useMemo(() => {
    let filtered = [...courses];

    if (search) {
      filtered = filtered.filter(course =>
        course.title.toLowerCase().includes(search.toLowerCase()) ||
        course.description.toLowerCase().includes(search.toLowerCase())
      );
    }

    if (category && category !== 'all') {
      filtered = filtered.filter(course => course.category === category);
    }
    return filtered;
  }, [search, category, courses]);

  const fetchCourses = async () => {
    try {
      const response = await axios.get(`${API}/courses?status=published`);
      setCourses(response.data);
    } catch (error) {
      console.error('Error fetching courses:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="catalog-page" data-testid="course-catalog">
      <Navbar user={user} logout={logout} />

      <div className="catalog-container">
        <div className="catalog-header">
          <h1 data-testid="catalog-title">Explore Courses</h1>
          <p>Discover your next learning adventure</p>
        </div>

        <div className="catalog-filters" data-testid="course-filters">
          <div className="search-bar">
            <Search className="search-icon" />
            <Input
              data-testid="search-input"
              type="text"
              placeholder="Search courses..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
          </div>

          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger data-testid="category-filter" className="category-select">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {categories.map(cat => (
                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {loading ? (
          <div className="loading" data-testid="loading">Loading courses...</div>
        ) : (
          <div className="courses-grid" data-testid="courses-grid">
            {filteredCourses.length === 0 ? (
              <div className="no-courses" data-testid="no-courses">No courses found</div>
            ) : (
              filteredCourses.map((course) => (
                <div key={course.id} className="course-card" data-testid={`course-card-${course.id}`}>
                  <div className="course-thumbnail">
                    <img src={course.thumbnail || '/placeholder-course.png'} alt={course.title} />
                  </div>
                  <div className="course-content">
                    <span className="course-category">{course.category}</span>
                    <h3 className="course-title">{course.title}</h3>
                    <p className="course-description">{course.description.substring(0, 120)}...</p>
                    <div className="course-footer">
                      <span className="course-price" data-testid={`price-${course.id}`}>${course.price}</span>
                      <Button
                        data-testid={`view-course-${course.id}`}
                        onClick={() => navigate(`/course/${course.id}`)}
                        size="sm"
                      >
                        View Details
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}