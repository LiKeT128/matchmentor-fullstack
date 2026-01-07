"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.services.email_service import send_welcome_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response schema for authentication endpoints."""
    user_id: int
    email: str
    tier: str
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response schema for user profile."""
    id: int
    email: str
    tier: str
    steam_id: str | None
    is_active: bool


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Register a new user.
    
    Args:
        request: Registration data with email and password.
        db: Database session.
        
    Returns:
        User info and access token.
        
    Raises:
        HTTPException: If email already exists.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password length
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Create user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        tier="FREE"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send welcome email (non-blocking)
    try:
        send_welcome_email(user.email)
    except Exception:
        pass  # Don't fail registration if email fails
    
    # Generate access token
    access_token = create_access_token(user.id)
    
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        tier=user.tier,
        access_token=access_token
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Login user and return access token.
    
    Args:
        request: Login credentials.
        db: Database session.
        
    Returns:
        User info and access token.
        
    Raises:
        HTTPException: If credentials are invalid.
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Generate access token
    access_token = create_access_token(user.id)
    
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        tier=user.tier,
        access_token=access_token
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user's profile.
    
    Args:
        current_user: Authenticated user from token.
        
    Returns:
        User profile data.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        tier=current_user.tier,
        steam_id=current_user.steam_id,
        is_active=current_user.is_active
    )


@router.post("/link-steam")
async def link_steam(
    steam_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Link Steam account to user profile.
    
    Args:
        steam_id: Steam ID to link.
        current_user: Authenticated user.
        db: Database session.
        
    Returns:
        Success message.
        
    Raises:
        HTTPException: If Steam ID already linked.
    """
    # Check if Steam ID already linked to another account
    existing = db.query(User).filter(
        User.steam_id == steam_id,
        User.id != current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Steam ID already linked to another account"
        )
    
    current_user.steam_id = steam_id
    db.commit()
    
    return {"status": "success", "message": "Steam account linked"}
