import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { BookOpen, Mail, ArrowLeft, CheckCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            await axios.post(`${API}/auth/forgot-password`, { email });
            setSubmitted(true);
            toast.success('Reset link sent if account exists');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    if (submitted) {
        return (
            <div className="auth-page">
                <div className="auth-container">
                    <div className="auth-header">
                        <CheckCircle className="auth-logo text-green-500" size={48} />
                        <h1>Check Your Email</h1>
                        <p>We've sent a password reset link to <strong>{email}</strong></p>
                    </div>
                    <div className="mt-6 text-center">
                        <Link to="/login" className="text-primary hover:underline flex items-center justify-center gap-2">
                            <ArrowLeft size={16} />
                            Back to Login
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-page">
            <div className="auth-container">
                <div className="auth-header">
                    <BookOpen className="auth-logo" />
                    <h1>Forgot Password</h1>
                    <p>Enter your email and we'll send you a link to reset your password.</p>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <Label htmlFor="email">Email Address</Label>
                        <div className="relative">
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="your@email.com"
                                className="pl-10"
                                required
                            />
                            <Mail className="absolute left-3 top-3 text-gray-400" size={18} />
                        </div>
                    </div>

                    <Button
                        type="submit"
                        className="w-full"
                        disabled={loading}
                    >
                        {loading ? 'Sending Link...' : 'Send Reset Link'}
                    </Button>
                </form>

                <div className="auth-footer">
                    <Link to="/login" className="text-sm text-primary hover:underline flex items-center justify-center gap-2">
                        <ArrowLeft size={16} />
                        Back to Login
                    </Link>
                </div>
            </div>
        </div>
    );
}
