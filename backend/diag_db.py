from app.database import SessionLocal
from app.models.match import Match
import json
import os

def check_db():
    db = SessionLocal()
    try:
        # Check for pending matches
        pending = db.query(Match).filter(Match.result == 'pending').all()
        print(f"--- DATABASE STATUS ---")
        print(f"Total pending matches: {len(pending)}")
        for m in pending:
            status = m.parsed_data.get('status') if m.parsed_data else 'N/A'
            print(f"ID: {m.id}, MatchID: {m.match_id}, Status: {status}, Created: {m.id}")
            
        # Check for recent completed matches
        recent = db.query(Match).order_by(Match.id.desc()).limit(5).all()
        print(f"\n--- RECENT MATCHES ---")
        for m in recent:
            print(f"ID: {m.id}, MatchID: {m.match_id}, Result: {m.result}, Hero: {m.hero_name}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
