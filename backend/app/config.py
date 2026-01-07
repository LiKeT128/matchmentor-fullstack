"""Application configuration using environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/matchmentor"
    
    # Authentication
    jwt_secret: str = "your-secret-key-change-this"
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 24
    
    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    
    # SendGrid
    sendgrid_api_key: str = ""
    from_email: str = "noreply@matchmentor.com"
    
    # Clarity Parser
    clarity_jar_path: str = "/app/clarity.jar"
    java_path: str = "java"
    
    # Application
    debug: bool = False
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
