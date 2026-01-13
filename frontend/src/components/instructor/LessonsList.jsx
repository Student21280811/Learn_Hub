import React from 'react';
import { Button } from '@/components/ui/button';
import { Video, FileText, BookOpen, Trash2 } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function LessonsList({ lessons, courseId, onRefresh }) {
  const getLessonIcon = (type) => {
    switch (type) {
      case 'video': return <Video size={20} />;
      case 'pdf': return <FileText size={20} />;
      default: return <BookOpen size={20} />;
    }
  };

  const handleDelete = async (lessonId) => {
    if (!window.confirm('Are you sure you want to delete this lesson?')) return;

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/lessons/${lessonId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Lesson deleted successfully');
      onRefresh();
    } catch (error) {
      toast.error('Failed to delete lesson');
      console.error(error);
    }
  };

  if (lessons.length === 0) {
    return (
      <div className="empty-state" data-testid="no-lessons">
        <p>No lessons added yet</p>
        <p className="text-sm text-gray-500">Click "Add Lesson" to create your first lesson</p>
      </div>
    );
  }

  return (
    <div className="lessons-management" data-testid="lessons-list">
      {lessons.map((lesson, index) => (
        <div key={lesson.id} className="lesson-manage-card" data-testid={`lesson-${lesson.id}`}>
          <div className="lesson-number">{index + 1}</div>
          <div className="lesson-icon">
            {getLessonIcon(lesson.type)}
          </div>
          <div className="lesson-details">
            <h4>{lesson.title}</h4>
            <div className="lesson-meta">
              <span className="lesson-type">{lesson.type}</span>
              {lesson.duration && <span>{lesson.duration} min</span>}
            </div>
          </div>
          <div className="lesson-actions">
            <Button
              data-testid={`delete-lesson-${lesson.id}`}
              variant="ghost"
              size="sm"
              onClick={() => handleDelete(lesson.id)}
            >
              <Trash2 size={16} className="text-red-500" />
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}