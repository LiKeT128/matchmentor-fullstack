"""Payments API endpoints for Stripe integration."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
import stripe

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.payment import Payment
from app.services.auth_service import get_current_user
from app.services.email_service import email_service

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.stripe_api_key

# Pricing (in cents)
TIER_PRICES = {
    "PRO": 500,       # $5.00/month
    "PREMIUM": 2000,  # $20.00/month
}


class CreateCheckoutRequest(BaseModel):
    """Request schema for creating checkout session."""
    tier: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response schema for checkout session."""
    checkout_url: str
    session_id: str


class PaymentResponse(BaseModel):
    """Response schema for payment record."""
    id: int
    amount: int
    status: str
    tier: str | None
    created_at: str


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CheckoutResponse:
    """
    Create a Stripe checkout session for subscription upgrade.
    
    Args:
        request: Checkout request with tier selection.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        Checkout URL to redirect user to.
        
    Raises:
        HTTPException: If tier invalid or Stripe error.
    """
    tier = request.tier.upper()
    
    if tier not in TIER_PRICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Choose from: {', '.join(TIER_PRICES.keys())}"
        )
    
    if current_user.tier == tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You are already on the {tier} tier"
        )
    
    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                metadata={"user_id": current_user.id}
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
        success_url = request.success_url or f"{settings.frontend_url}/upgrade/success"
        cancel_url = request.cancel_url or f"{settings.frontend_url}/upgrade"
        
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"MatchMentor {tier}",
                        "description": f"Monthly {tier} subscription"
                    },
                    "unit_amount": TIER_PRICES[tier],
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "user_id": current_user.id,
                "tier": tier
            }
        )
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment service error. Please try again."
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
) -> dict:
    """
    Handle Stripe webhook events.
    
    Args:
        request: Raw request body.
        stripe_signature: Stripe signature header.
        db: Database session.
        
    Returns:
        Success acknowledgment.
        
    Raises:
        HTTPException: If signature invalid.
    """
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    # Handle specific events
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_checkout_completed(session, db)
    
    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        await _handle_payment_succeeded(invoice, db)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await _handle_subscription_cancelled(subscription, db)
    
    return {"status": "received"}


async def _handle_checkout_completed(session: dict, db: Session) -> None:
    """Handle successful checkout session."""
    user_id = session.get("metadata", {}).get("user_id")
    tier = session.get("metadata", {}).get("tier")
    
    if not user_id or not tier:
        logger.warning(f"Missing metadata in checkout session: {session.get('id')}")
        return
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        logger.warning(f"User not found: {user_id}")
        return
    
    # Update user tier
    old_tier = user.tier
    user.tier = tier
    
    # Create payment record
    payment = Payment(
        user_id=user.id,
        amount=session.get("amount_total", 0),
        stripe_id=session.get("payment_intent") or session.get("id"),
        status="completed",
        tier=tier,
        description=f"Upgrade from {old_tier} to {tier}"
    )
    db.add(payment)
    db.commit()
    
    # Send confirmation email
    try:
        email_service.send_tier_upgrade_confirmation(user.email, tier)
    except Exception:
        pass
    
    logger.info(f"User {user_id} upgraded to {tier}")


async def _handle_payment_succeeded(invoice: dict, db: Session) -> None:
    """Handle successful recurring payment."""
    customer_id = invoice.get("customer")
    
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return
    
    # Create payment record
    payment = Payment(
        user_id=user.id,
        amount=invoice.get("amount_paid", 0),
        stripe_id=invoice.get("id"),
        status="completed",
        tier=user.tier,
        description="Monthly subscription renewal"
    )
    db.add(payment)
    db.commit()
    
    logger.info(f"Recurring payment processed for user {user.id}")


async def _handle_subscription_cancelled(subscription: dict, db: Session) -> None:
    """Handle subscription cancellation."""
    customer_id = subscription.get("customer")
    
    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return
    
    # Downgrade to free tier
    user.tier = "FREE"
    db.commit()
    
    logger.info(f"User {user.id} downgraded to FREE tier")


@router.get("/history", response_model=list[PaymentResponse])
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[PaymentResponse]:
    """
    Get current user's payment history.
    
    Args:
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        List of payment records.
    """
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).limit(50).all()
    
    return [
        PaymentResponse(
            id=p.id,
            amount=p.amount,
            status=p.status,
            tier=p.tier,
            created_at=p.created_at.isoformat()
        )
        for p in payments
    ]
