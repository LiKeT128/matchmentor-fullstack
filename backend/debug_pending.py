#!/usr/bin/env python3
"""
Debug script to check pending matches in database.
"""

import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.match import Match

def check_pending_matches():
    """Check what's in pending matches."""
    db = SessionLocal()
    try:
        matches = db.query(Match).filter(Match.hero_name == 'pending').all()
        print(f'Found {len(matches)} matches with pending status')
        
        if matches:
            match = matches[0]
            print(f'Match ID: {match.match_id}')
            print(f'Hero name: {match.hero_name}')
            print(f'Duration: {match.duration_minutes}')
            
            if match.parsed_data:
                print(f'Parsed data keys: {list(match.parsed_data.keys())}')
                print(f'Players in parsed_data: {len(match.parsed_data.get("players", []))}')
                print(f'Heroes in parsed_data: {len(match.parsed_data.get("heroes", []))}')
                
                # Check if there's any hero data at all
                if 'players' in match.parsed_data:
                    players = match.parsed_data['players']
                    print(f'First player keys: {list(players[0].keys()) if players else "No players"}')
                    if players:
                        print(f'First player: {players[0]}')
                else:
                    print('No players key in parsed_data')
                    
                # Check for raw data
                if 'raw' in match.parsed_data:
                    raw = match.parsed_data['raw']
                    print(f'Raw data keys: {list(raw.keys()) if raw else "No raw"}')
                    if raw and 'players' in raw:
                        print(f'Raw players count: {len(raw["players"])}')
                        if raw['players']:
                            print(f'First raw player: {raw["players"][0]}')
            else:
                print('No parsed_data at all')
                
            print(f'Metrics: {match.metrics}')
            print(f'Overall score: {match.overall_score if match.overall_score else "Not calculated"}')
                
    finally:
        db.close()

if __name__ == "__main__":
    check_pending_matches()
