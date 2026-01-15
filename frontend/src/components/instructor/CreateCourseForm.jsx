import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { X, Sparkles, Plus, Trash2, ArrowRight, ArrowLeft, Check, BookOpen, Clock, DollarSign, Image as ImageIcon, Search } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const categories = ['Programming', 'Design', 'Business', 'Marketing', 'Photography', 'Music', 'Health', 'Language'];
const levels = ['Beginner', 'Intermediate', 'Advanced'];
const languages = ['English', 'Spanish', 'French', 'German', 'Chinese', 'Arabic', 'Hindi', 'Portuguese'];

export default function CreateCourseForm({ onClose, onSuccess }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(null); // 'description', 'requirements', 'outcomes'
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: 'Programming',
    level: 'Beginner',
    language: 'English',
    requirements: [''],
    outcomes: [''],
    faqs: [{ question: '', answer: '' }],
    price: '',
    discount_price: '',
    thumbnail: '',
    video_platform: 'youtube',
    preview_video: '',
    meta_keywords: '',
    meta_description: '',
    drip_content: false
  });

  const nextStep = () => {
    if (step === 1 && (!formData.title || !formData.description)) {
      toast.error('Please fill in title and description');
      return;
    }
    setStep(prev => Math.min(prev + 1, 6));
  };

  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  const handleAddField = (field) => {
    if (field === 'faqs') {
      setFormData({ ...formData, faqs: [...formData.faqs, { question: '', answer: '' }] });
    } else {
      setFormData({ ...formData, [field]: [...formData[field], ''] });
    }
  };

  const handleRemoveField = (field, index) => {
    const list = [...formData[field]];
    list.splice(index, 1);
    setFormData({ ...formData, [field]: list });
  };

  const handleFieldChange = (field, index, value) => {
    const list = [...formData[field]];
    list[index] = value;
    setFormData({ ...formData, [field]: list });
  };

  const handleFaqChange = (index, field, value) => {
    const list = [...formData.faqs];
    list[index][field] = value;
    setFormData({ ...formData, faqs: list });
  };

  const generateWithAI = async (target) => {
    if (!formData.title) {
      toast.error('Please enter a course title first');
      return;
    }

    setAiGenerating(target);
    try {
      let prompt = '';
      if (target === 'description') {
        prompt = `Generate a compelling course description for a course titled "${formData.title}" in the ${formData.category} category. Keep it to 2-3 sentences.`;
      } else if (target === 'requirements') {
        prompt = `List 3-4 professional requirements for a course titled "${formData.title}". Return as a simple list separated by newlines.`;
      } else if (target === 'outcomes') {
        prompt = `List 3-4 key learning outcomes for a course titled "${formData.title}". Return as a simple list separated by newlines.`;
      }

      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/ai/course-assistant?prompt=${encodeURIComponent(prompt)}`, null, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const aiContent = response.data.response;

      if (target === 'description') {
        setFormData(prev => ({ ...prev, description: aiContent }));
      } else {
        const items = aiContent.split('\n').filter(i => i.trim()).map(i => i.replace(/^[0-9*.-]\s*/, '').trim());
        setFormData(prev => ({ ...prev, [target]: items }));
      }

      toast.success(`AI ${target} generated!`);
    } catch (error) {
      toast.error(`Failed to generate ${target}`);
    } finally {
      setAiGenerating(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const payload = {
        ...formData,
        price: parseFloat(formData.price) || 0,
        discount_price: formData.discount_price ? parseFloat(formData.discount_price) : null,
        requirements: formData.requirements.filter(r => r.trim()),
        outcomes: formData.outcomes.filter(o => o.trim()),
        faqs: formData.faqs.filter(f => f.question.trim() && f.answer.trim())
      };

      await axios.post(`${API}/courses`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Course created successfully!');
      onSuccess();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create course');
    } finally {
      setLoading(false);
    }
  };

  const getDiscountPercentage = () => {
    if (!formData.price || !formData.discount_price) return 0;
    const p = parseFloat(formData.price);
    const d = parseFloat(formData.discount_price);
    if (p <= 0) return 0;
    return Math.round(((p - d) / p) * 100);
  };

  const renderStepIndicator = () => {
    const stepIcons = [BookOpen, Plus, DollarSign, ImageIcon, Search, Check];
    const stepNames = ['Basic', 'Info', 'Pricing', 'Media', 'SEO', 'Finish'];

    return (
      <div className="wizard-progress">
        {stepNames.map((name, i) => {
          const Icon = stepIcons[i];
          const active = step === i + 1;
          const completed = step > i + 1;
          return (
            <div key={name} className={`progress-step ${active ? 'active' : ''} ${completed ? 'completed' : ''}`}>
              <div className="step-icon-wrapper">
                {completed ? <Check size={16} /> : <Icon size={16} />}
              </div>
              <span>{name}</span>
              {i < stepNames.length - 1 && <div className="step-line" />}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="modal-overlay" data-testid="create-course-form">
      <div className="modal-content course-wizard-modal">
        <div className="modal-header">
          <h2>Create New Course</h2>
          <button onClick={onClose} className="close-btn">
            <X size={24} />
          </button>
        </div>

        {renderStepIndicator()}

        <form onSubmit={handleSubmit} className="wizard-form">
          {step === 1 && (
            <div className="wizard-step-content">
              <div className="form-group">
                <Label htmlFor="title">Course Title *</Label>
                <Input
                  id="title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g. Complete Web Development Bootcamp"
                  required
                />
              </div>
              <div className="form-group">
                <div className="label-with-action">
                  <Label htmlFor="description">Short Description *</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => generateWithAI('description')}
                    disabled={!!aiGenerating}
                  >
                    <Sparkles size={14} className="mr-1" />
                    {aiGenerating === 'description' ? 'Generating...' : 'AI Writer'}
                  </Button>
                </div>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Highlight what makes this course special..."
                  rows={4}
                  required
                />
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <Label>Category</Label>
                  <Select value={formData.category} onValueChange={(v) => setFormData({ ...formData, category: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="form-group">
                  <Label>Difficulty Level</Label>
                  <Select value={formData.level} onValueChange={(v) => setFormData({ ...formData, level: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {levels.map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="form-group">
                  <Label>Language</Label>
                  <Select value={formData.language} onValueChange={(v) => setFormData({ ...formData, language: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {languages.map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="wizard-step-content">
              <div className="repeater-section">
                <div className="label-with-action">
                  <Label>Requirements</Label>
                  <Button type="button" variant="ghost" size="sm" onClick={() => generateWithAI('requirements')} disabled={!!aiGenerating}>
                    <Sparkles size={14} className="mr-1" /> AI Suggest
                  </Button>
                </div>
                {formData.requirements.map((req, i) => (
                  <div key={`req-${i}`} className="repeater-item">
                    <Input value={req} onChange={(e) => handleFieldChange('requirements', i, e.target.value)} placeholder="e.g. Basic JavaScript knowledge" />
                    <Button type="button" variant="ghost" size="icon" onClick={() => handleRemoveField('requirements', i)} disabled={formData.requirements.length === 1}>
                      <Trash2 size={16} />
                    </Button>
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={() => handleAddField('requirements')} className="mt-2">
                  <Plus size={14} className="mr-1" /> Add Requirement
                </Button>
              </div>

              <div className="repeater-section mt-6">
                <div className="label-with-action">
                  <Label>Learning Outcomes</Label>
                  <Button type="button" variant="ghost" size="sm" onClick={() => generateWithAI('outcomes')} disabled={!!aiGenerating}>
                    <Sparkles size={14} className="mr-1" /> AI Suggest
                  </Button>
                </div>
                {formData.outcomes.map((out, i) => (
                  <div key={`out-${i}`} className="repeater-item">
                    <Input value={out} onChange={(e) => handleFieldChange('outcomes', i, e.target.value)} placeholder="e.g. Build real-world React apps" />
                    <Button type="button" variant="ghost" size="icon" onClick={() => handleRemoveField('outcomes', i)} disabled={formData.outcomes.length === 1}>
                      <Trash2 size={16} />
                    </Button>
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={() => handleAddField('outcomes')} className="mt-2">
                  <Plus size={14} className="mr-1" /> Add Outcome
                </Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="wizard-step-content">
              <div className="form-grid">
                <div className="form-group">
                  <Label>Price (USD)</Label>
                  <Input type="number" step="0.01" value={formData.price} onChange={(e) => setFormData({ ...formData, price: e.target.value })} placeholder="49.99" />
                </div>
                <div className="form-group">
                  <div className="label-with-action">
                    <Label>Discount Price (Optional)</Label>
                    {getDiscountPercentage() > 0 && <span className="discount-tag">{getDiscountPercentage()}% OFF</span>}
                  </div>
                  <Input type="number" step="0.01" value={formData.discount_price} onChange={(e) => setFormData({ ...formData, discount_price: e.target.value })} placeholder="29.99" />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <input type="checkbox" id="drip" checked={formData.drip_content} onChange={(e) => setFormData({ ...formData, drip_content: e.target.checked })} />
                <Label htmlFor="drip" className="cursor-pointer">Enable Drip Content (Schedule content release)</Label>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="wizard-step-content">
              <div className="form-group">
                <Label>Thumbnail URL</Label>
                <div className="input-with-preview">
                  <Input value={formData.thumbnail} onChange={(e) => setFormData({ ...formData, thumbnail: e.target.value })} placeholder="https://..." />
                  {formData.thumbnail && <div className="thumb-preview"><img src={formData.thumbnail} alt="Preview" /></div>}
                </div>
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <Label>Preview Video Platform</Label>
                  <Select value={formData.video_platform} onValueChange={(v) => setFormData({ ...formData, video_platform: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="youtube">YouTube</SelectItem>
                      <SelectItem value="vimeo">Vimeo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="form-group">
                  <Label>Preview Video URL</Label>
                  <Input value={formData.preview_video} onChange={(e) => setFormData({ ...formData, preview_video: e.target.value })} placeholder="URL to trailer" />
                </div>
              </div>
            </div>
          )}

          {step === 5 && (
            <div className="wizard-step-content">
              <div className="form-group">
                <Label>Meta Keywords</Label>
                <Input value={formData.meta_keywords} onChange={(e) => setFormData({ ...formData, meta_keywords: e.target.value })} placeholder="react, web dev, coding (comma separated)" />
              </div>
              <div className="form-group">
                <Label>Meta Description</Label>
                <Textarea value={formData.meta_description} onChange={(e) => setFormData({ ...formData, meta_description: e.target.value })} placeholder="Description for search engines..." rows={4} />
              </div>
            </div>
          )}

          {step === 6 && (
            <div className="wizard-step-content finish-step">
              <div className="finish-illustration">
                <Check size={48} />
              </div>
              <h3>Almost Ready!</h3>
              <p>Review your course details and click submit to create your course record. You can manage curriculum (lessons/sections) after this step.</p>
              <div className="course-summary-card">
                <h4>{formData.title || 'Untitled Course'}</h4>
                <p>{formData.category} • {formData.level} • {formData.language}</p>
                <p className="price-summary">{formData.discount_price ? `$${formData.discount_price} (was $${formData.price})` : (formData.price ? `$${formData.price}` : 'Free')}</p>
              </div>
            </div>
          )}

          <div className="wizard-actions">
            <Button type="button" variant="outline" onClick={step === 1 ? onClose : prevStep}>
              {step === 1 ? 'Cancel' : 'Back'}
            </Button>
            {step < 6 ? (
              <Button type="button" onClick={nextStep}>
                Next <ArrowRight size={16} className="ml-2" />
              </Button>
            ) : (
              <Button type="submit" disabled={loading}>
                {loading ? 'Creating...' : 'Create Course & Continue'}
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}