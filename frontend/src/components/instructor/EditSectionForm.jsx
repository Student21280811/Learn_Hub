import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { X } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function EditSectionForm({ section, onClose, onSuccess }) {
    const [formData, setFormData] = useState({
        title: section.title || '',
        description: section.description || '',
        order: section.order || 1
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (section) {
            setFormData({
                title: section.title || '',
                description: section.description || '',
                order: section.order || 1
            });
        }
    }, [section]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const token = localStorage.getItem('token');
            await axios.patch(`${API}/sections/${section.id}`, {
                ...formData,
                order: parseInt(formData.order)
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            toast.success('Section updated successfully!');
            onSuccess();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to update section');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" data-testid="edit-section-form">
            <div className="modal-content">
                <div className="modal-header">
                    <h2>Edit Section</h2>
                    <button onClick={onClose} className="close-btn">
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="section-form" style={{ padding: '1.5rem' }}>
                    <div className="form-group">
                        <Label htmlFor="title">Section Title *</Label>
                        <Input
                            id="title"
                            data-testid="edit-section-title-input"
                            value={formData.title}
                            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            placeholder="e.g., Getting Started, Advanced Concepts"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <Label htmlFor="description">Description (Optional)</Label>
                        <Textarea
                            id="description"
                            data-testid="edit-section-description-input"
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            placeholder="Brief description of this section..."
                            rows={3}
                        />
                    </div>

                    <div className="form-group">
                        <Label htmlFor="order">Section Order *</Label>
                        <Input
                            id="order"
                            data-testid="edit-section-order-input"
                            type="number"
                            min="1"
                            value={formData.order}
                            onChange={(e) => setFormData({ ...formData, order: e.target.value })}
                            required
                        />
                    </div>

                    <div className="form-actions">
                        <Button type="button" variant="outline" onClick={onClose}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading} data-testid="update-section-btn">
                            {loading ? 'Updating...' : 'Update Section'}
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    );
}
