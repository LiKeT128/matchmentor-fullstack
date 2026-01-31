import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.opendota_client import get_opendota_client

async def test_polling():
    # Use a real match ID
    match_id = "8642447925" 
    
    print(f"--- TESTING OPENDOTA POLLING WORKFLOW FOR {match_id} ---")
    client = get_opendota_client()
    
    # 1. Initial Fetch
    print("Fetching match data...")
    match_data = await client.get_match(match_id)
    
    is_parsed = client.is_data_complete(match_data)
    print(f"Initial Parse Status: {'COMPLETE' if is_parsed else 'BASIC'}")
    
    if not is_parsed:
        print("Requesting deep parse...")
        success = await client.request_parse(match_id)
        print(f"Request status: {'SUCCESS' if success else 'FAILED'}")
        
        if success:
            print("Starting poll (simulated for 1 attempt)...")
            # We don't want to wait 3 minutes in a test, just check once
            await asyncio.sleep(2)
            match_data = await client.get_match(match_id)
            print(f"Poll Result Parse Status: {'COMPLETE' if client.is_data_complete(match_data) else 'STILL BASIC'}")

    print("\n--- TEST FINISHED ---")

if __name__ == "__main__":
    asyncio.run(test_polling())
