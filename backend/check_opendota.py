
import asyncio
import aiohttp
import sys

MATCH_ID = "8640421359"
if len(sys.argv) > 1:
    MATCH_ID = sys.argv[1]

async def check():
    url = f"https://api.opendota.com/api/matches/{MATCH_ID}"
    print(f"Checking {url}...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            print(f"Status: {resp.status}")
            try:
                if resp.status == 200:
                    data = await resp.json()
                    print("Data found!")
                    players = data.get("players", [])
                    print(f"Players count: {len(players)}")
                    if players:
                         print(f"Sample Hero ID: {players[0].get('hero_id')}")
                else:
                    print("Response:", await resp.text())
            except Exception as e:
                print(f"Error reading response: {e}")

if __name__ == "__main__":
    asyncio.run(check())
