"""Tests for authentication endpoints."""

import pytest


class TestAuthEndpoints:
    """Test suite for /api/auth endpoints."""
    
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 201
        data = response.json()
        
        assert "access_token" in data
        assert data["email"] == "newuser@example.com"
        assert data["tier"] == "FREE"
        assert data["token_type"] == "bearer"
    
    def test_register_duplicate_email(self, client):
        """Test registration with existing email."""
        # First registration
        client.post("/api/auth/register", json={
            "email": "duplicate@example.com",
            "password": "password123"
        })
        
        # Second registration with same email
        response = client.post("/api/auth/register", json={
            "email": "duplicate@example.com",
            "password": "different123"
        })
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_short_password(self, client):
        """Test registration with short password."""
        response = client.post("/api/auth/register", json={
            "email": "shortpass@example.com",
            "password": "short"
        })
        
        assert response.status_code == 400
        assert "8 characters" in response.json()["detail"]
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "password123"
        })
        
        assert response.status_code == 422
    
    def test_login_success(self, client):
        """Test successful login."""
        # Register first
        client.post("/api/auth/register", json={
            "email": "login@example.com",
            "password": "password123"
        })
        
        # Login
        response = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["email"] == "login@example.com"
    
    def test_login_wrong_password(self, client):
        """Test login with wrong password."""
        # Register
        client.post("/api/auth/register", json={
            "email": "wrongpass@example.com",
            "password": "correctpassword"
        })
        
        # Login with wrong password
        response = client.post("/api/auth/login", json={
            "email": "wrongpass@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 401
    
    def test_get_me_authenticated(self, client, auth_headers):
        """Test getting current user profile."""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "test@example.com"
        assert data["tier"] == "FREE"
        assert data["is_active"] == True
    
    def test_get_me_unauthenticated(self, client):
        """Test getting profile without auth."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 403  # No credentials
    
    def test_get_me_invalid_token(self, client):
        """Test getting profile with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
