import React, { useState } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { X, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function AddQuizForm({ courseId, onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [questions, setQuestions] = useState([
    { question: '', questionType: 'single', numOptions: 4, options: ['', '', '', ''], correct_answer: 0 }
  ]);
  const [loading, setLoading] = useState(false);

  const addQuestion = () => {
    setQuestions([...questions, { question: '', questionType: 'single', numOptions: 4, options: ['', '', '', ''], correct_answer: 0 }]);
  };

  const removeQuestion = (index) => {
    setQuestions(questions.filter((_, i) => i !== index));
  };

  const updateQuestion = (index, field, value) => {
    const newQuestions = [...questions];
    newQuestions[index][field] = value;
    setQuestions(newQuestions);
  };

  const updateQuestionType = (qIndex, type) => {
    const newQuestions = [...questions];
    if (type === 'truefalse') {
      newQuestions[qIndex].questionType = 'truefalse';
      newQuestions[qIndex].numOptions = 2;
      newQuestions[qIndex].options = ['True', 'False'];
      newQuestions[qIndex].correct_answer = 0;
    } else {
      newQuestions[qIndex].questionType = 'single';
      newQuestions[qIndex].numOptions = 4;
      newQuestions[qIndex].options = ['', '', '', ''];
      newQuestions[qIndex].correct_answer = 0;
    }
    setQuestions(newQuestions);
  };

  const updateNumOptions = (qIndex, num) => {
    const newQuestions = [...questions];
    const numOpts = parseInt(num) || 2;
    const clampedNum = Math.max(2, Math.min(6, numOpts));

    const currentOptions = newQuestions[qIndex].options;
    let newOptions = [];

    for (let i = 0; i < clampedNum; i++) {
      newOptions.push(currentOptions[i] || '');
    }

    newQuestions[qIndex].numOptions = clampedNum;
    newQuestions[qIndex].options = newOptions;

    // Reset correct answer if it's out of bounds
    if (newQuestions[qIndex].correct_answer >= clampedNum) {
      newQuestions[qIndex].correct_answer = 0;
    }

    setQuestions(newQuestions);
  };

  const updateOption = (qIndex, oIndex, value) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].options[oIndex] = value;
    setQuestions(newQuestions);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      // Clean up questions before sending (remove extra fields)
      const cleanedQuestions = questions.map(q => ({
        question: q.question,
        options: q.options,
        correct_answer: q.correct_answer
      }));

      await axios.post(`${API}/quizzes`, {
        course_id: courseId,
        title,
        questions: cleanedQuestions
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Quiz added successfully!');
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add quiz');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" data-testid="add-quiz-form">
      <div className="modal-content quiz-modal">
        <div className="modal-header">
          <h2>Create Quiz</h2>
          <button onClick={onClose} className="close-btn">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="quiz-form" style={{ padding: '1.5rem', maxHeight: '70vh', overflowY: 'auto' }}>
          <div className="form-group">
            <Label htmlFor="title">Quiz Title *</Label>
            <Input
              id="title"
              data-testid="quiz-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Module 1 Quiz"
              required
            />
          </div>

          <div className="questions-section">
            <div className="section-header">
              <h3>Questions</h3>
              <Button type="button" size="sm" onClick={addQuestion} data-testid="add-question-btn">
                <Plus size={16} className="mr-1" />
                Add Question
              </Button>
            </div>

            {questions.map((q, qIndex) => (
              <div key={qIndex} className="question-card" data-testid={`question-${qIndex}`}>
                <div className="question-header">
                  <h4>Question {qIndex + 1}</h4>
                  {questions.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeQuestion(qIndex)}
                      className="remove-btn"
                      data-testid={`remove-question-${qIndex}`}
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>

                <div className="form-group">
                  <Label>Question Text *</Label>
                  <Input
                    value={q.question}
                    onChange={(e) => updateQuestion(qIndex, 'question', e.target.value)}
                    placeholder="What is...?"
                    required
                    data-testid={`question-text-${qIndex}`}
                  />
                </div>

                {/* Question Type Dropdown */}
                <div className="form-group">
                  <Label>Question Type</Label>
                  <select
                    value={q.questionType}
                    onChange={(e) => updateQuestionType(qIndex, e.target.value)}
                    className="w-full p-2 border rounded-md bg-white"
                    style={{ height: '40px', borderColor: '#e2e8f0' }}
                    data-testid={`question-type-${qIndex}`}
                  >
                    <option value="single">Single choice And true/false</option>
                    <option value="truefalse">True/False Only</option>
                  </select>
                </div>

                {/* Number of Options */}
                {q.questionType !== 'truefalse' && (
                  <div className="form-group">
                    <Label>Number of options</Label>
                    <Input
                      type="number"
                      min="2"
                      max="6"
                      value={q.numOptions}
                      onChange={(e) => updateNumOptions(qIndex, e.target.value)}
                      data-testid={`num-options-${qIndex}`}
                    />
                  </div>
                )}

                {/* Options with Radio on RIGHT */}
                <div className="options-group">
                  {q.options.map((option, oIndex) => (
                    <div key={oIndex} className="form-group" style={{ marginBottom: '0.75rem' }}>
                      <Label>Option {oIndex + 1}</Label>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Input
                          value={option}
                          onChange={(e) => updateOption(qIndex, oIndex, e.target.value)}
                          placeholder={q.questionType === 'truefalse' ? (oIndex === 0 ? 'True' : 'False') : `Option ${oIndex + 1}`}
                          required
                          style={{ flex: 1 }}
                          data-testid={`option-${qIndex}-${oIndex}`}
                        />
                        <input
                          type="radio"
                          name={`correct-${qIndex}`}
                          checked={q.correct_answer === oIndex}
                          onChange={() => updateQuestion(qIndex, 'correct_answer', oIndex)}
                          style={{ width: '20px', height: '20px', cursor: 'pointer' }}
                          data-testid={`correct-answer-${qIndex}-${oIndex}`}
                        />
                      </div>
                    </div>
                  ))}
                  <p className="help-text" style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                    Select the radio button for the correct answer
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="form-actions">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading} data-testid="submit-quiz-btn">
              {loading ? 'Creating...' : 'Create Quiz'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}