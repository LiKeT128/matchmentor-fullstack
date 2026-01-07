"""Tests for coaching marketplace functionality."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.models.coach import Coach
from app.models.booking import Booking, BookingStatus
from app.models.review import Review


class TestCoachingMarketplace:
    """Test suite for Coaching Marketplace."""
    
    @pytest.fixture
    def coach_headers(self, client, db):
        """Create a registered coach user."""
        # Clean up existing coach with same email if any
        from app.models.user import User
        db.query(User).filter(User.email == "coach@test.com").delete()
        db.query(Coach).filter(Coach.user_id == 123456).delete() # dummy filter
        db.commit()
        
        response = client.post("/api/auth/register", json={
            "email": "coach@test.com",
            "password": "password123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_register_coach(self, client, coach_headers, db):
        """Test registering as a coach."""
        response = client.post(
            "/api/coaches/register",
            json={
                "hourly_rate": 2000,  # $20.00
                "bio": "Pro coach",
                "experience_years": 5,
                "specialties": ["Carry", "Support"]
            },
            headers=coach_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["hourly_rate"] == 2000
        assert data["verified"] is True
        
        # Verify in DB
        coach = db.query(Coach).filter(Coach.hourly_rate == 2000).first()
        assert coach is not None
    
    def test_list_coaches(self, client, db):
        """Test listing coaches."""
        response = client.get("/api/coaches")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @patch("stripe.PaymentIntent.create")
    @patch("stripe.Customer.create")
    def test_book_session(self, mock_customer, mock_intent, client, auth_headers, coach_headers):
        """Test booking a session."""
        # 1. Register a coach first
        client.post(
            "/api/coaches/register",
            json={"hourly_rate": 2000, "bio": "Test", "experience_years": 5},
            headers=coach_headers
        )
        
        # Get coach ID
        response = client.get("/api/coaches")
        coach_id = response.json()[0]["id"]
        
        # 2. Book session as student (auth_headers)
        mock_intent.return_value = MagicMock(id="pi_test", client_secret="secret")
        mock_customer.return_value = MagicMock(id="cus_test")
        
        start_time = datetime.utcnow().isoformat()
        
        book_response = client.post(
            "/api/sessions/book",
            json={
                "coach_id": coach_id,
                "scheduled_time": start_time,
                "notes": "Help me improve"
            },
            headers=auth_headers
        )
        
        assert book_response.status_code == 201
        data = book_response.json()
        assert data["coach_id"] == coach_id
        assert data["status"] == "confirmed"
    
    def test_book_own_session_fails(self, client, coach_headers):
        """Test coach cannot book their own session."""
        # Register
        client.post(
            "/api/coaches/register",
            json={"hourly_rate": 2000, "bio": "Test", "experience_years": 5},
            headers=coach_headers
        )
        
        response = client.get("/api/coaches")
        coach_id = response.json()[0]["id"]
        
        # Try to book
        start_time = datetime.utcnow().isoformat()
        response = client.post(
            "/api/sessions/book",
            json={"coach_id": coach_id, "scheduled_time": start_time},
            headers=coach_headers
        )
        
        assert response.status_code == 400
        assert "own session" in response.json()["detail"]

    def test_leave_review(self, client, auth_headers, coach_headers, db):
        """Test leaving a review."""
        # 1. Setup Coach, Session
        # Register coach
        c_res = client.post("/api/coaches/register", 
            json={"hourly_rate": 2000, "bio": "Test", "experience_years": 5}, 
            headers=coach_headers
        )
        coach_id = c_res.json()["id"]
        
        # Book session
        with patch("stripe.PaymentIntent.create") as mock_intent, \
             patch("stripe.Customer.create") as mock_customer:
            mock_intent.return_value = MagicMock(id="pi_test")
            mock_customer.return_value = MagicMock(id="cus_test")
            start_time = datetime.utcnow()
            
            b_res = client.post("/api/sessions/book",
                json={"coach_id": coach_id, "scheduled_time": start_time.isoformat()},
                headers=auth_headers
            )
            session_id = b_res.json()["id"]
        
        # 2. Leave Review
        review_res = client.post(
            f"/api/sessions/{session_id}/review",
            json={"rating": 5, "comment": "Great session!"},
            headers=auth_headers
        )
        
        assert review_res.status_code == 200
        assert review_res.json()["status"] == "review_saved"
        assert review_res.json()["new_rating"] == 5.0
        
        # 3. Leave Another Review (Should Fail)
        dup_res = client.post(
            f"/api/sessions/{session_id}/review",
            json={"rating": 1, "comment": "Bad!"},
            headers=auth_headers
        )
        assert dup_res.status_code == 400
        assert "already exists" in dup_res.json()["detail"]
