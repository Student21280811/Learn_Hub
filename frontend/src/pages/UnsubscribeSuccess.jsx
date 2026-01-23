import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function UnsubscribeSuccess() {
    const [searchParams] = useSearchParams();

    return (
        <div className="unsubscribe-page">
            <div className="unsubscribe-container">
                <CheckCircle size={80} className="success-icon" />

                <h1>Unsubscribed Successfully</h1>

                <p className="message">
                    You won't receive our weekly newsletter anymore.
                </p>

                <p className="info">
                    We're sorry to see you go! If you change your mind,
                    you can always resubscribe from our homepage.
                </p>

                <div className="actions">
                    <Link to="/">
                        <Button>
                            <ArrowLeft size={18} className="mr-2" />
                            Return to Homepage
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    );
}
