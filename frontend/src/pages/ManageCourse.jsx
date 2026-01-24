import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Navbar from '@/components/Navbar';
import AddLessonForm from '@/components/instructor/AddLessonForm';
import EditLessonForm from '@/components/instructor/EditLessonForm';
import AddSectionForm from '@/components/instructor/AddSectionForm';
import EditSectionForm from '@/components/instructor/EditSectionForm';
import AddLiveClassForm from '@/components/instructor/AddLiveClassForm';
import AddQuizForm from '@/components/instructor/AddQuizForm';
import LessonsList from '@/components/instructor/LessonsList';
import { Plus, ArrowLeft, FolderPlus, Video, HelpCircle, Trash2, Edit } from 'lucide-react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ManageCourse({ user, logout }) {
  const { id } = useParams();
  const [course, setCourse] = useState(null);
  const [sections, setSections] = useState([]);
  const [lessons, setLessons] = useState([]);
  const [liveClasses, setLiveClasses] = useState([]);
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddLesson, setShowAddLesson] = useState(false);
  const [showAddSection, setShowAddSection] = useState(false);
  const [showAddLiveClass, setShowAddLiveClass] = useState(false);
  const [showAddQuiz, setShowAddQuiz] = useState(false);
  const [editingLesson, setEditingLesson] = useState(null);
  const [editingSection, setEditingSection] = useState(null);
  const [selectedSectionId, setSelectedSectionId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchCourseData();
  }, [id]);

  const fetchCourseData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [courseRes, sectionsRes, lessonsRes, liveClassesRes, quizzesRes] = await Promise.all([
        axios.get(`${API}/courses/${id}`, { headers }),
        axios.get(`${API}/courses/${id}/sections`, { headers }),
        axios.get(`${API}/courses/${id}/lessons`, { headers }),
        axios.get(`${API}/courses/${id}/live-classes`, { headers }),
        axios.get(`${API}/quizzes/${id}`, { headers })
      ]);

      const courseData = courseRes.data;

      // Ownership check for instructors
      if (user?.role === 'instructor') {
        const instructorsRes = await axios.get(`${API}/instructors`, { headers });
        const myInstructorProfile = instructorsRes.data.find(i => i.user_id === user.id);

        if (!myInstructorProfile || myInstructorProfile.id !== courseData.instructor_id) {
          toast.error('You do not have permission to manage this course');
          navigate('/dashboard/instructor');
          return;
        }
      }

      setCourse(courseData);
      setSections(sectionsRes.data);
      setLessons(lessonsRes.data);
      setLiveClasses(liveClassesRes.data);
      setQuizzes(quizzesRes.data);
    } catch (error) {
      toast.error('Failed to load course');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handlePublish = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`${API}/courses/${id}`, { status: 'published' }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course published successfully!');
      fetchCourseData();
    } catch (error) {
      toast.error('Failed to publish course');
    }
  };

  const handleUnpublish = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`${API}/courses/${id}`, { status: 'draft' }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course unpublished');
      fetchCourseData();
    } catch (error) {
      toast.error('Failed to unpublish course');
    }
  };

  const handleDeleteCourse = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/courses/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Course deleted successfully');
      navigate('/dashboard/instructor');
    } catch (error) {
      toast.error('Failed to delete course');
      console.error(error);
    }
  };

  const handleDeleteQuiz = async (quizId) => {
    if (!window.confirm('Delete this quiz permanently?')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/quizzes/${quizId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Quiz deleted');
      fetchCourseData();
    } catch (error) {
      toast.error('Failed to delete quiz');
    }
  };

  const handleDeleteLiveClass = async (liveClassId) => {
    if (!window.confirm('Delete this live class?')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/live-classes/${liveClassId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Live class deleted');
      fetchCourseData();
    } catch (error) {
      toast.error('Failed to delete live class');
    }
  };

  const handleDeleteSection = async (sectionId) => {
    if (!window.confirm('Delete this section and all its lessons?')) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/sections/${sectionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Section deleted');
      fetchCourseData();
    } catch (error) {
      toast.error('Failed to delete section');
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (!course) return <div>Course not found</div>;

  return (
    <div className="manage-course-page" data-testid="manage-course">
      <Navbar user={user} logout={logout} />

      <div className="dashboard-container">
        <div className="course-manage-header">
          <div>
            <Button
              variant="ghost"
              onClick={() => navigate('/dashboard/instructor')}
              data-testid="back-btn"
            >
              <ArrowLeft size={18} className="mr-2" />
              Back to Dashboard
            </Button>
            <h1 data-testid="course-title">{course.title}</h1>
            <div className="course-meta-info">
              <span className={`status-badge ${course.status}`}>
                {course.status}
              </span>
              <span>{lessons.length} Lessons</span>
            </div>
          </div>
          <div className="header-actions" style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {course.status === 'draft' ? (
              <Button
                data-testid="publish-btn"
                onClick={handlePublish}
              >
                Publish Course
              </Button>
            ) : (
              <Button
                data-testid="unpublish-btn"
                onClick={handleUnpublish}
                variant="outline"
              >
                Unpublish
              </Button>
            )}

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" data-testid="delete-course-btn">
                  <Trash2 size={18} className="mr-2" />
                  Delete Course
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone. This will permanently delete the course,
                    all its lessons, sections, quizzes, and associated content.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDeleteCourse} className="bg-red-600 hover:bg-red-700 text-white border-transparent">
                    Delete Permanently
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        <Tabs defaultValue="structure" className="dashboard-tabs">
          <TabsList>
            <TabsTrigger value="structure" data-testid="structure-tab">Course Structure</TabsTrigger>
            <TabsTrigger value="live-classes" data-testid="live-classes-tab">Live Classes ({liveClasses.length})</TabsTrigger>
            <TabsTrigger value="quizzes" data-testid="quizzes-tab">Quizzes ({quizzes.length})</TabsTrigger>
            <TabsTrigger value="details" data-testid="details-tab">Details</TabsTrigger>
          </TabsList>

          <TabsContent value="structure">
            <div className="structure-section">
              <div className="section-header">
                <h2>Course Structure</h2>
                <div className="action-buttons" style={{ display: 'flex', gap: '4px' }}>
                  <Button
                    data-testid="add-section-btn"
                    onClick={() => setShowAddSection(true)}
                    variant="ghost"
                    size="sm"
                    title="Add Section"
                  >
                    <FolderPlus size={16} className="text-gray-500" />
                  </Button>
                  <Button
                    data-testid="add-lesson-btn"
                    onClick={() => setShowAddLesson(true)}
                    variant="ghost"
                    size="sm"
                    title="Add Lesson"
                  >
                    <Plus size={16} className="text-gray-500" />
                  </Button>
                </div>
              </div>

              {sections.length === 0 && lessons.length === 0 ? (
                <div className="empty-state">
                  <p>No content added yet</p>
                  <p className="text-sm text-gray-500">Start by adding sections to organize your course, then add lessons</p>
                </div>
              ) : (
                <div className="course-structure">
                  {sections.map((section, sIndex) => (
                    <div key={section.id} className="section-block" data-testid={`section-${section.id}`}>
                      <div className="section-header-block">
                        <div>
                          <h3>Section {sIndex + 1}: {section.title}</h3>
                          {section.description && <p className="section-desc">{section.description}</p>}
                        </div>
                        <div className="section-actions" style={{ display: 'flex', gap: '4px' }}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditingSection(section)}
                            title="Edit section"
                          >
                            <Edit size={16} className="text-gray-500" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteSection(section.id)}
                            title="Delete section"
                          >
                            <Trash2 size={16} className="text-red-500" />
                          </Button>
                        </div>
                      </div>

                      {section.lessons && section.lessons.length > 0 ? (
                        <div className="section-lessons">
                          <LessonsList
                            lessons={section.lessons}
                            courseId={id}
                            onRefresh={fetchCourseData}
                            onEdit={(lesson) => setEditingLesson(lesson)}
                          />
                        </div>
                      ) : (
                        <div className="empty-section">No lessons in this section yet</div>
                      )}
                    </div>
                  ))}

                  {lessons.filter(l => !l.section_id).length > 0 && (
                    <div className="section-block">
                      <div className="section-header-block">
                        <h3>Standalone Lessons</h3>
                      </div>
                      <div className="section-lessons">
                        <LessonsList
                          lessons={lessons.filter(l => !l.section_id)}
                          courseId={id}
                          onRefresh={fetchCourseData}
                          onEdit={(lesson) => setEditingLesson(lesson)}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="live-classes">
            <div className="live-classes-section">
              <div className="section-header">
                <h2>Live Classes</h2>
                <Button
                  data-testid="add-live-class-btn"
                  onClick={() => setShowAddLiveClass(true)}
                >
                  <Video size={18} className="mr-2" />
                  Schedule Live Class
                </Button>
              </div>

              {liveClasses.length === 0 ? (
                <div className="empty-state">
                  <p>No live classes scheduled yet</p>
                </div>
              ) : (
                <div className="live-classes-list">
                  {liveClasses.map((liveClass) => (
                    <div key={liveClass.id} className="live-class-card" data-testid={`live-class-${liveClass.id}`}>
                      <div className="live-class-info">
                        <h4>{liveClass.title}</h4>
                        <p>{liveClass.description}</p>
                        <div className="live-class-meta">
                          <span>{new Date(liveClass.scheduled_at).toLocaleString()}</span>
                          <span>{liveClass.duration} minutes</span>
                          <span className={`status-badge ${liveClass.status}`}>{liveClass.status}</span>
                        </div>
                      </div>
                      <div className="live-class-actions">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteLiveClass(liveClass.id)}
                          data-testid={`delete-live-${liveClass.id}`}
                        >
                          <Trash2 size={16} className="text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="quizzes">
            <div className="quizzes-section">
              <div className="section-header">
                <h2>Quizzes</h2>
                <Button
                  data-testid="add-quiz-btn"
                  onClick={() => setShowAddQuiz(true)}
                >
                  <HelpCircle size={18} className="mr-2" />
                  Create Quiz
                </Button>
              </div>

              {quizzes.length === 0 ? (
                <div className="empty-state">
                  <p>No quizzes created yet</p>
                </div>
              ) : (
                <div className="quizzes-list">
                  {quizzes.map((quiz) => (
                    <div key={quiz.id} className="quiz-card" data-testid={`quiz-${quiz.id}`}>
                      <div className="flex items-center flex-1">
                        <HelpCircle size={24} className="quiz-icon" />
                        <div>
                          <h4>{quiz.title}</h4>
                          <p>{quiz.questions.length} questions</p>
                        </div>
                      </div>
                      <div className="quiz-actions">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteQuiz(quiz.id)}
                          data-testid={`delete-quiz-${quiz.id}`}
                        >
                          <Trash2 size={16} className="text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="details">
            <div className="course-details-view">
              <div className="detail-card">
                <h3>Course Information</h3>
                <div className="detail-item">
                  <label>Title:</label>
                  <p>{course.title}</p>
                </div>
                <div className="detail-item">
                  <label>Description:</label>
                  <p>{course.description}</p>
                </div>
                <div className="detail-item">
                  <label>Category:</label>
                  <p>{course.category}</p>
                </div>
                <div className="detail-item">
                  <label>Price:</label>
                  <p>${course.price}</p>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {
        showAddSection && (
          <AddSectionForm
            courseId={id}
            onClose={() => setShowAddSection(false)}
            onSuccess={() => {
              setShowAddSection(false);
              fetchCourseData();
            }}
          />
        )
      }

      {
        showAddLesson && (
          <AddLessonForm
            courseId={id}
            sectionId={selectedSectionId}
            onClose={() => {
              setShowAddLesson(false);
              setSelectedSectionId(null);
            }}
            onSuccess={() => {
              setShowAddLesson(false);
              setSelectedSectionId(null);
              fetchCourseData();
            }}
          />
        )
      }

      {
        editingLesson && (
          <EditLessonForm
            lesson={editingLesson}
            onClose={() => setEditingLesson(null)}
            onSuccess={() => {
              setEditingLesson(null);
              fetchCourseData();
            }}
          />
        )
      }

      {
        editingSection && (
          <EditSectionForm
            section={editingSection}
            onClose={() => setEditingSection(null)}
            onSuccess={() => {
              setEditingSection(null);
              fetchCourseData();
            }}
          />
        )
      }

      {
        showAddLiveClass && (
          <AddLiveClassForm
            courseId={id}
            onClose={() => setShowAddLiveClass(false)}
            onSuccess={() => {
              setShowAddLiveClass(false);
              fetchCourseData();
            }}
          />
        )
      }

      {
        showAddQuiz && (
          <AddQuizForm
            courseId={id}
            onClose={() => setShowAddQuiz(false)}
            onSuccess={() => {
              setShowAddQuiz(false);
              fetchCourseData();
            }}
          />
        )
      }
    </div >
  );
}
