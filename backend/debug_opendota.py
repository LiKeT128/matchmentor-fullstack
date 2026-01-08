import asyncio
import aiohttp
import json

MATCH_ID = "8634348084"

async def fetch_match():
    async with aiohttp.ClientSession() as session:
        url = f"https://api.opendota.com/api/matches/{MATCH_ID}"
        print(f"Fetching {url}...")
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
            
            data = await response.json()
            print("Received data keys:", list(data.keys()))
            
            if "players" in data:
                print(f"Player count: {len(data['players'])}")
                for i, p in enumerate(data['players'][:10]):
                    print(f"Player {i}: hero_id={p.get('hero_id')}, hero_name={p.get('hero_name')}")
            else:
                print("No 'players' key found!")

if __name__ == "__main__":
    asyncio.run(fetch_match())
