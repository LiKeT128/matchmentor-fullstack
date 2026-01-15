#!/usr/bin/env python3
"""
Clean up pending matches with invalid data.
"""

import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.match import Match

def cleanup_pending_matches():
    """Remove matches with invalid parsed data."""
    db = SessionLocal()
    try:
        # Find matches with invalid data
        bad_matches = db.query(Match).filter(
            Match.hero_name == 'pending'
        ).all()
        
        print(f'Found {len(bad_matches)} pending matches to clean up')
        
        for match in bad_matches:
            print(f'Removing match {match.id}: {match.match_id}')
            db.delete(match)
        
        db.commit()
        print('✅ Cleanup completed')
        
    except Exception as e:
        print(f'❌ Cleanup failed: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_pending_matches()
