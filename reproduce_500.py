import asyncio
import os
import sys
import logging
from unittest.mock import MagicMock

# Setup environment
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["OPENDOTA_API_KEY"] = ""

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reproduce_error():
    print("--- STARTING LOCAL REPRODUCTION ---")
    
    match_id = "8671820075"

    try:
        # Import the router function directly to test logic
        from app.api.matches import lookup_match
        from app.models.match import Match
        
        # REAL DB SESSION (SQlite in memory)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine("sqlite:///:memory:")
        Match.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # REAL USER
        current_user = MagicMock()
        current_user.id = 1
        
        print(f"Calling lookup_match for {match_id} with REAL logic involved...")
        
        # Call the function
        result = await lookup_match(
            match_id=match_id,
            steam_id=None,
            current_user=current_user,
            db=db
        )
        
        print("SUCCESS! Result:", result)

    except Exception as e:
        print("\n!!! CAUGHT EXCEPTION !!!")
        print(f"Type: {type(e)}")
        print(f"Message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce_error())
