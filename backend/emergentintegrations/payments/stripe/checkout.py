"""
Stripe Checkout stub implementation using stripe directly.
This replaces the emergentintegrations Stripe checkout functionality.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import stripe


@dataclass
class CheckoutSessionRequest:
    """Request to create a checkout session"""
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckoutSessionResponse:
    """Response from creating a checkout session"""
    session_id: str
    url: str


@dataclass
class CheckoutStatusResponse:
    """Response for checkout status"""
    payment_status: str
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class StripeCheckout:
    """Stripe Checkout implementation"""
    
    def __init__(self, api_key: str, webhook_url: str = ""):
        self.api_key = api_key
        self.webhook_url = webhook_url
        stripe.api_key = api_key
    
    async def create_checkout_session(
        self, 
        request: CheckoutSessionRequest,
        instructor_stripe_account_id: Optional[str] = None
    ) -> CheckoutSessionResponse:
        """Create a Stripe checkout session with optional payment splitting"""
        try:
            # Convert amount to cents
            amount_cents = int(request.amount * 100)
            
            # Prepare checkout session parameters
            session_params = {
                "payment_method_types": ["card"],
                "line_items": [{
                    "price_data": {
                        "currency": request.currency,
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": "Course Purchase",
                        },
                    },
                    "quantity": 1,
                }],
                "mode": "payment",
                "success_url": request.success_url,
                "cancel_url": request.cancel_url,
                "metadata": request.metadata,
            }
            
            # Add payment splitting if instructor has Stripe account connected
            if instructor_stripe_account_id:
                # Calculate platform fee (10%)
                platform_fee_cents = int(amount_cents * 0.10)
                
                # Configure payment to split: 90% to instructor, 10% to platform
                session_params["payment_intent_data"] = {
                    "application_fee_amount": platform_fee_cents,
                    "transfer_data": {
                        "destination": instructor_stripe_account_id
                    }
                }
            
            session = stripe.checkout.Session.create(**session_params)
            
            return CheckoutSessionResponse(
                session_id=session.id,
                url=session.url
            )
        except Exception as e:
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    async def get_checkout_status(self, session_id: str) -> CheckoutStatusResponse:
        """Get the status of a checkout session"""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            # Ensure metadata is a standard dict
            metadata = dict(session.metadata) if session.metadata else {}
            return CheckoutStatusResponse(
                payment_status=session.payment_status,
                session_id=session_id,
                metadata=metadata
            )
        except Exception as e:
            raise Exception(f"Failed to get checkout status: {str(e)}")
    
    async def handle_webhook(self, body: bytes, signature: str) -> Dict[str, Any]:
        """Handle Stripe webhook"""
        # For now, just return success
        # In production, you would verify the webhook signature
        return {"received": True}
