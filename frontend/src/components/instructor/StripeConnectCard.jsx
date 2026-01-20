import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { CheckCircle, AlertCircle, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import './StripeConnect.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function StripeConnectCard() {
    const [stripeStatus, setStripeStatus] = useState({ connected: false, loading: true });

    useEffect(() => {
        fetchStripeStatus();
    }, []);

    const fetchStripeStatus = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API}/payments/stripe/status`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setStripeStatus({ ...response.data, loading: false });
        } catch (error) {
            console.error('Failed to fetch Stripe status:', error);
            setStripeStatus({ connected: false, loading: false });
        }
    };

    const handleConnectStripe = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${API}/payments/stripe/connect`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            // Redirect to Stripe OAuth
            window.location.href = response.data.url;
        } catch (error) {
            toast.error('Failed to initiate Stripe connection');
            console.error(error);
        }
    };

    if (stripeStatus.loading) {
        return (
            <div className="stripe-connect-card loading">
                <p>Checking payment setup...</p>
            </div>
        );
    }

    return (
        <div className={`stripe-connect-card ${stripeStatus.connected ? 'connected' : 'disconnected'}`}>
            <div className="stripe-header">
                <h3>Payment Setup</h3>
                {stripeStatus.connected ? (
                    <div className="status-badge success">
                        <CheckCircle size={18} />
                        <span>Payouts Active</span>
                    </div>
                ) : (
                    <div className="status-badge warning">
                        <AlertCircle size={18} />
                        <span>Not Connected</span>
                    </div>
                )}
            </div>

            <div className="stripe-content">
                {stripeStatus.connected ? (
                    <>
                        <p className="success-message">
                            ✅ Your Stripe account is connected! You'll automatically receive 90% of course sales.
                        </p>
                        <div className="stripe-details">
                            <small>Account ID: {stripeStatus.stripe_account_id}</small>
                        </div>
                    </>
                ) : (
                    <>
                        <p className="warning-message">
                            Connect your Stripe account to receive automatic payouts (90% of each sale).
                        </p>
                        <p className="info-message">
                            <strong>Without Stripe connected:</strong> Payments will be held and paid manually.
                        </p>
                        <Button
                            onClick={handleConnectStripe}
                            className="connect-stripe-btn"
                            data-testid="connect-stripe-btn"
                        >
                            <ExternalLink size={18} className="mr-2" />
                            Connect Stripe Account
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
}
