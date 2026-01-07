"""Tests for payments and monetization functionality."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.email_service import email_service


class TestTierLimits:
    """Test tier limit enforcement."""
    
    def test_free_tier_limit_is_5(self, client, auth_headers):
        """Test FREE tier has 5 match limit."""
        from app.api.matches import TIER_LIMITS
        assert TIER_LIMITS.get("FREE") == 5
    
    def test_pro_tier_limit_is_50(self, client, auth_headers):
        """Test PRO tier has 50 match limit."""
        from app.api.matches import TIER_LIMITS
        assert TIER_LIMITS.get("PRO") == 50
    
    def test_premium_tier_is_unlimited(self, client, auth_headers):
        """Test PREMIUM tier is unlimited."""
        from app.api.matches import TIER_LIMITS
        assert TIER_LIMITS.get("PREMIUM") == float("inf")


class TestStripeIntegration:
    """Test Stripe payment integration."""
    
    def test_tier_prices_correct(self):
        """Test tier prices are set correctly."""
        from app.api.payments import TIER_PRICES
        assert TIER_PRICES["PRO"] == 500        # $5.00
        assert TIER_PRICES["PREMIUM"] == 2000   # $20.00
    
    @patch("stripe.Customer.create")
    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session(
        self, 
        mock_session, 
        mock_customer,
        client, 
        auth_headers
    ):
        """Test checkout session creation."""
        mock_customer.return_value = MagicMock(id="cus_test123")
        mock_session.return_value = MagicMock(
            id="cs_test123",
            url="https://checkout.stripe.com/test"
        )
        
        response = client.post(
            "/api/payments/create-checkout",
            json={"tier": "PRO"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        assert "session_id" in data
    
    def test_invalid_tier_rejected(self, client, auth_headers):
        """Test invalid tier is rejected."""
        response = client.post(
            "/api/payments/create-checkout",
            json={"tier": "INVALID"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid tier" in response.json()["detail"]
    
    @patch("stripe.Webhook.construct_event")
    def test_webhook_checkout_completed(self, mock_event, client, db):
        """Test webhook processes checkout.session.completed."""
        from app.models.user import User
        
        # Create test user
        user = User(email="webhook@test.com", password_hash="hash", tier="FREE")
        db.add(user)
        db.commit()
        
        mock_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test",
                    "metadata": {"user_id": str(user.id), "tier": "PRO"},
                    "amount_total": 500,
                    "customer": "cus_test"
                }
            }
        }
        
        response = client.post(
            "/api/payments/webhook",
            content=b"test payload",
            headers={"Stripe-Signature": "test_sig"}
        )
        
        assert response.status_code == 200
        
        # Verify user tier updated
        db.refresh(user)
        assert user.tier == "PRO"
    
    @patch("stripe.Webhook.construct_event")
    def test_webhook_subscription_cancelled(self, mock_event, client, db):
        """Test webhook handles subscription cancellation."""
        from app.models.user import User
        
        # Create test user with PRO tier
        user = User(
            email="cancel@test.com", 
            password_hash="hash", 
            tier="PRO",
            stripe_customer_id="cus_cancel"
        )
        db.add(user)
        db.commit()
        
        mock_event.return_value = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {"customer": "cus_cancel"}
            }
        }
        
        response = client.post(
            "/api/payments/webhook",
            content=b"test payload",
            headers={"Stripe-Signature": "test_sig"}
        )
        
        assert response.status_code == 200
        
        # Verify user downgraded to FREE
        db.refresh(user)
        assert user.tier == "FREE"


class TestEmailService:
    """Test email service functionality."""
    
    def test_email_service_initialization(self):
        """Test email service initializes."""
        assert email_service is not None
    
    @patch.object(email_service, "_send_email")
    def test_welcome_email_content(self, mock_send):
        """Test welcome email has correct structure."""
        mock_send.return_value = True
        
        result = email_service.send_welcome_email("test@example.com")
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Welcome to MatchMentor" in call_args[1]["subject"]
        assert "5 replay analyses" in call_args[1]["html_content"]
    
    @patch.object(email_service, "_send_email")
    def test_tier_upgrade_email(self, mock_send):
        """Test tier upgrade email for PRO tier."""
        mock_send.return_value = True
        
        result = email_service.send_tier_upgrade_confirmation("test@example.com", "PRO")
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "PRO" in call_args[1]["subject"]
    
    @patch.object(email_service, "_send_email")
    def test_match_analysis_email(self, mock_send):
        """Test match analysis complete email."""
        mock_send.return_value = True
        
        result = email_service.send_match_analysis_complete(
            "test@example.com",
            match_id="123",
            hero_name="Invoker",
            score=85
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Invoker" in call_args[1]["subject"]


class TestPaymentHistory:
    """Test payment history endpoint."""
    
    def test_payment_history_empty(self, client, auth_headers):
        """Test empty payment history."""
        response = client.get("/api/payments/history", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_payment_history_with_records(self, client, auth_headers, db):
        """Test payment history with records."""
        from app.models.payment import Payment
        from app.models.user import User
        
        # Get test user
        user = db.query(User).first()
        
        # Create payment record
        payment = Payment(
            user_id=user.id,
            amount=500,
            stripe_id="pi_test",
            status="completed",
            tier="PRO"
        )
        db.add(payment)
        db.commit()
        
        response = client.get("/api/payments/history", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["amount"] == 500
        assert data[0]["tier"] == "PRO"
