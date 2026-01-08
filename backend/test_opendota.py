import asyncio
import aiohttp
import json

async def test_opendota(match_id):
    url = f"https://api.opendota.com/api/matches/{match_id}"
    print(f"Fetching {url}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
            data = await response.json()
            print("Response received.")
            
            if "players" in data:
                print(f"Player count: {len(data['players'])}")
                for i, p in enumerate(data["players"]):
                    print(f"Player {i}: hero_id={p.get('hero_id')}, hero_name={p.get('hero_name')}")
            else:
                print("No 'players' key in response")

if __name__ == "__main__":
    asyncio.run(test_opendota("8636759340"))
