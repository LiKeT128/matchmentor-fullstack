
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password

def create_test_user():
    db = SessionLocal()
    try:
        email = "test@example.com"
        password = "password123"
        
        # Check if exists
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Creating test user {email}...")
            user = User(
                email=email,
                password_hash=hash_password(password),
                tier="FREE",
                is_active=True
            )
            db.add(user)
            db.commit()
            print("User created successfully.")
        else:
            print(f"User {email} already exists.")
            # Ensure password matches (reset it)
            user.password_hash = hash_password(password)
            db.commit()
            print("Password reset to 'password123'.")
            
        print("\n=== CREDENTIALS ===")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print("===================")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
