import sys
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path to import models if needed, but raw SQL is easier here
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Database URL (from main.py or config, assuming default local)
# The user's metadata says postgres is running. I'll guess the URL or try to find it.
# backend/app/main.py might have it. Or I can use the one from start.sh/Procfile if visible.
# Usually: postgresql://postgres:postgres@localhost:5432/matchmentor
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/matchmentor"

def inspect_match(match_id):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Use simple text query to avoid importing all models
        result = session.execute(text(f"SELECT parsed_data FROM matches WHERE match_id = '{match_id}'"))
        row = result.fetchone()
        
        if not row:
            print(f"Match {match_id} not found.")
            return

        parsed_data = row[0]
        if not parsed_data:
            print("parsed_data is None/Empty")
            return

        print("--- parsed_data keys ---")
        print(list(parsed_data.keys()))

        if 'players' in parsed_data:
            players = parsed_data['players']
            print(f"--- players count: {len(players)} ---")
            if players:
                p0 = players[0]
                print("--- Player 0 keys ---")
                print(list(p0.keys()))
                
                # Check for time series specifically
                ts_keys = ['gold_t', 'xp_t', 'lh_t', 'last_hits_t', 'times']
                print("--- Time Series Check ---")
                for k in ts_keys:
                    print(f"{k}: {'FOUND' if k in p0 else 'MISSING'}")
                    
        if 'full_data' in parsed_data:
            print("--- full_data check ---")
            full = parsed_data['full_data']
            print(f"full_data keys: {list(full.keys())}")
            # Check players inside full_data if different
            if 'players' in full:
                print(f"full_data['players'][0] keys: {list(full['players'][0].keys())}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_match("8627882837")
