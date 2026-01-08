import asyncio
import aiohttp
import json

async def fetch_heroes():
    url = "https://api.opendota.com/api/heroes"
    print(f"Fetching {url}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error: {response.status}")
                return
            data = await response.json()
            print("Response received.")
            
            # Format as python dict
            print("HERO_MAP = {")
            for h in data:
                print(f"    {h['id']}: \"{h['name']}\",")
            print("}")

if __name__ == "__main__":
    asyncio.run(fetch_heroes())
