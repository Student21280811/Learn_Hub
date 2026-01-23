"""
Newsletter API Routes for LearnHub
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from datetime import datetime, timezone
import logging
import os
import uuid
from newsletter import generate_weekly_blog, send_weekly_newsletter

logger = logging.getLogger(__name__)

# Create newsletter router
newsletter_router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@newsletter_router.post("/subscribe")
async def subscribe_to_newsletter(email: EmailStr, db):
    """Subscribe to weekly newsletter"""
    try:
        # Check if already subscribed
        existing = await db.email_subscriptions.find_one({"email": email})
        
        if existing:
            if existing['subscribed']:
                return {"message": "Already subscribed",  "success": False}
            else:
                # Resubscribe
                await db.email_subscriptions.update_one(
                    {"email": email},
                    {"$set": {"subscribed": True, "subscription_date": datetime.now(timezone.utc)}}
                )
                return {"message": "Resubscribed successfully!", "success": True}
        
        # Create new subscription
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": None,
            "email": email,
            "subscribed": True,
            "unsubscribe_token": str(uuid.uuid4()),
            "subscription_date": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.email_subscriptions.insert_one(doc)
        
        logger.info(f"New newsletter subscription: {email}")
        return {"message": "Subscribed successfully!", "success": True}
        
    except Exception as e:
        logger.error(f"Subscription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to subscribe")


@newsletter_router.get("/unsubscribe")
async def unsubscribe_from_newsletter(token: str, db):
    """Unsubscribe using token from email link"""
    try:
        subscription = await db.email_subscriptions.find_one({"unsubscribe_token": token})
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Invalid unsubscribe link")
        
        await db.email_subscriptions.update_one(
            {"unsubscribe_token": token},
            {"$set": {"subscribed": False}}
        )
        
        logger.info(f"Unsubscribed: {subscription['email']}")
        
        # Redirect to frontend
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(url=f"{frontend_url}/unsubscribe-success")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsubscribe")
