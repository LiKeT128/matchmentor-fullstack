import asyncio
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.opendota_client import OpenDotaClient

async def fetch_and_save(match_id):
    client = OpenDotaClient()
    print(f"Fetching match {match_id} from OpenDota...")
    data = await client.get_match(match_id)
    
    if data:
        output_file = f"backend/{match_id}_opendota.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved to {output_file}")
    else:
        print("❌ Failed to fetch match data")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_json.py <match_id>")
        sys.exit(1)
    
    match_id = sys.argv[1]
    asyncio.run(fetch_and_save(match_id))
