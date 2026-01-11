import sys
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/matchmentor"

def inspect_match(match_id):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        result = session.execute(text(f"SELECT parsed_data FROM matches WHERE match_id = '{match_id}'"))
        row = result.fetchone()
        
        if not row:
            print(f"Match {match_id} not found locally.")
            return

        parsed_data = row[0]
        if not parsed_data:
            print("parsed_data is None/Empty")
            return

        print(f"--- Inspecting Data for {match_id} ---")
        
        # Check source (opendota vs clarity)
        if 'parsing_method' in parsed_data:
             print(f"Parsing Source: {parsed_data['parsing_method']}")
        else:
             print("Parsing Source: Unknown (Likely OpenDota)")

        # Check players for time series
        if 'players' in parsed_data:
            players = parsed_data['players']
            print(f"Players count: {len(players)}")
            
            # Find Slark
            slark = next((p for p in players if p.get('hero_id') == 93 or p.get('hero_name') == 'npc_dota_hero_slark'), None) # Slark ID is 93
            
            if slark:
                print("--- Slark Found ---")
                ts_keys = ['gold_t', 'xp_t', 'lh_t', 'last_hits_t']
                found_any = False
                for k in ts_keys:
                    if k in slark:
                        print(f"  {k}: FOUND (Size: {len(slark[k])})")
                        found_any = True
                    else:
                        print(f"  {k}: MISSING")
                
                if not found_any:
                    print("  -> CRITICAL: No time-series data found for Slark.")
            else:
                print("Slark not found in players list?!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_match("8643428601")
