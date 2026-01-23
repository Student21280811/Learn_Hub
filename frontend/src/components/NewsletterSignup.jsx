import React, { useState } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Mail, CheckCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function NewsletterSignup() {
    const [email, setEmail] = useState('');
    const [subscribed, setSubscribed] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubscribe = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const response = await axios.post(`${API}/newsletter/subscribe`, { email });

            if (response.data.success) {
                setSubscribed(true);
                toast.success('📬 Subscribed! Check your inbox for weekly insights.');
                setEmail('');
            } else {
                toast.info(response.data.message);
            }
        } catch (error) {
            console.error('Subscribe error:', error);
            toast.error('Failed to subscribe. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    if (subscribed) {
        return (
            <div className="newsletter-signup subscribed">
                <CheckCircle size={48} className="success-icon" />
                <h3>✅ You're Subscribed!</h3>
                <p>Get ready for weekly learning insights delivered to your inbox.</p>
            </div>
        );
    }

    return (
        <div className="newsletter-signup">
            <div className="newsletter-icon">
                <Mail size={32} />
            </div>

            <h3>📬 Weekly Learning Insights</h3>
            <p>Get AI-curated course tips and learning strategies every week</p>

            <form onSubmit={handleSubscribe} className="newsletter-form">
                <input
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                    className="newsletter-input"
                />
                <Button
                    type="submit"
                    disabled={loading}
                    className="newsletter-button"
                >
                    {loading ? 'Subscribing...' : 'Subscribe Free'}
                </Button>
            </form>

            <small className="newsletter-disclaimer">
                Unsubscribe anytime • No spam, ever
            </small>
        </div>
    );
}
