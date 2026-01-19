import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { X } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function EditLessonForm({ lesson, onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        title: '',
        type: 'video',
        content_url: '',
        content_text: '',
        notes_url: '',
        duration: '',
        order: 1
    });
    const [loading, setLoading] = useState(false);
    const [uploadingPdf, setUploadingPdf] = useState(false);
    const [uploadingNotes, setUploadingNotes] = useState(false);

    useEffect(() => {
        if (lesson) {
            setFormData({
                title: lesson.title || '',
                type: lesson.type || 'video',
                content_url: lesson.content_url || '',
                content_text: lesson.content_text || '',
                notes_url: lesson.notes_url || '',
                duration: lesson.duration || '',
                order: lesson.order || 1
            });
        }
    }, [lesson]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const payload = {
                ...formData,
                duration: formData.duration ? parseInt(formData.duration) : null
            };

            const token = localStorage.getItem('token');
            await axios.patch(`${API}/lessons/${lesson.id}`, payload, {
                headers: { Authorization: `Bearer ${token}` }
            });

            toast.success('Lesson updated successfully!');
            onSuccess();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to update lesson');
        } finally {
            setLoading(false);
        }
    };

    const handlePdfUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.type !== 'application/pdf') {
            toast.error('Please select a PDF file');
            return;
        }

        const formDataUpload = new FormData();
        formDataUpload.append('file', file);

        setUploadingPdf(true);
        try {
            const token = localStorage.getItem('token');
            const response = await axios.post(`${API}/upload/lesson-pdf`, formDataUpload, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'multipart/form-data'
                }
            });

            setFormData(prev => ({ ...prev, content_url: `${BACKEND_URL}${response.data.url}` }));
            toast.success('PDF uploaded successfully!');
        } catch (error) {
            toast.error('Failed to upload PDF');
            console.error(error);
        } finally {
            setUploadingPdf(false);
        }
    };

    const handleNotesUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (file.type !== 'application/pdf') {
            toast.error('Please select a PDF file');
            return;
        }

        const formDataUpload = new FormData();
        formDataUpload.append('file', file);

        setUploadingNotes(true);
        try {
            const token = localStorage.getItem('token');
            const response = await axios.post(`${API}/upload/lesson-pdf`, formDataUpload, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'multipart/form-data'
                }
            });

            setFormData(prev => ({ ...prev, notes_url: `${BACKEND_URL}${response.data.url}` }));
            toast.success('Notes PDF uploaded successfully!');
        } catch (error) {
            toast.error('Failed to upload Notes PDF');
            console.error(error);
        } finally {
            setUploadingNotes(false);
        }
    };

    return (
        <div className="modal-overlay" data-testid="edit-lesson-form">
            <div className="modal-content lesson-form-modal">
                <div className="modal-header">
                    <h2>Edit Lesson</h2>
                    <button onClick={onClose} className="close-btn">
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="lesson-form">
                    <div className="form-group">
                        <Label htmlFor="title">Lesson Title *</Label>
                        <Input
                            id="title"
                            data-testid="lesson-title-input"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            placeholder="Introduction to Variables"
                            required
                        />
                    </div>

                    <div className="form-grid">
                        <div className="form-group">
                            <Label htmlFor="type">Content Type *</Label>
                            <Select
                                value={formData.type}
                                onValueChange={(value) => setFormData({ ...formData, type: value })}
                            >
                                <SelectTrigger data-testid="lesson-type-select">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="video">Video</SelectItem>
                                    <SelectItem value="text">Text</SelectItem>
                                    <SelectItem value="pdf">PDF</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="form-group">
                            <Label htmlFor="duration">Duration (minutes)</Label>
                            <Input
                                id="duration"
                                data-testid="lesson-duration-input"
                                type="number"
                                min="1"
                                value={formData.duration}
                                onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
                                placeholder="15"
                            />
                        </div>
                    </div>

                    {(formData.type === 'video' || formData.type === 'pdf') && (
                        <div className="form-group">
                            <div className="label-with-action">
                                <Label htmlFor="content_url">
                                    {formData.type === 'video' ? 'Video URL (YouTube/Vimeo)' : 'PDF URL'} *
                                </Label>
                                {formData.type === 'pdf' && (
                                    <div className="upload-actions">
                                        <Button
                                            type="button"
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => document.getElementById('pdf-upload').click()}
                                            disabled={uploadingPdf}
                                        >
                                            {uploadingPdf ? 'Uploading...' : 'Upload PDF'}
                                        </Button>
                                        <input
                                            id="pdf-upload"
                                            type="file"
                                            accept="application/pdf"
                                            onChange={handlePdfUpload}
                                            style={{ display: 'none' }}
                                        />
                                    </div>
                                )}
                            </div>
                            <Input
                                id="content_url"
                                data-testid="content-url-input"
                                value={formData.content_url}
                                onChange={(e) => setFormData({ ...formData, content_url: e.target.value })}
                                placeholder={formData.type === 'video' ? 'https://youtube.com/watch?v=...' : 'https://example.com/file.pdf'}
                                required
                            />
                        </div>
                    )}

                    {formData.type === 'text' && (
                        <div className="form-group">
                            <Label htmlFor="content_text">Lesson Content (HTML) *</Label>
                            <Textarea
                                id="content_text"
                                data-testid="content-text-input"
                                value={formData.content_text}
                                onChange={(e) => setFormData({ ...formData, content_text: e.target.value })}
                                placeholder="<h2>Introduction</h2><p>Content here...</p>"
                                rows={10}
                                required
                            />
                            <p className="text-sm text-gray-500 mt-1">You can use HTML tags for formatting</p>
                        </div>
                    )}

                    <div className="form-group border-t pt-4 mt-4">
                        <div className="label-with-action">
                            <Label htmlFor="notes_url">Supplementary Notes (PDF Attachment)</Label>
                            <div className="upload-actions">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => document.getElementById('notes-upload').click()}
                                    disabled={uploadingNotes}
                                >
                                    {uploadingNotes ? 'Uploading...' : 'Upload Notes PDF'}
                                </Button>
                                <input
                                    id="notes-upload"
                                    type="file"
                                    accept="application/pdf"
                                    onChange={handleNotesUpload}
                                    style={{ display: 'none' }}
                                />
                            </div>
                        </div>
                        <Input
                            id="notes_url"
                            value={formData.notes_url}
                            onChange={(e) => setFormData({ ...formData, notes_url: e.target.value })}
                            placeholder="Enter notes PDF URL or upload above"
                        />
                    </div>

                    <div className="form-group">
                        <Label htmlFor="order">Lesson Order *</Label>
                        <Input
                            id="order"
                            data-testid="lesson-order-input"
                            type="number"
                            min="1"
                            value={formData.order}
                            onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) })}
                            required
                        />
                    </div>

                    <div className="form-actions">
                        <Button type="button" variant="outline" onClick={onClose}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading} data-testid="submit-lesson-btn">
                            {loading ? 'Updating...' : 'Update Lesson'}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
