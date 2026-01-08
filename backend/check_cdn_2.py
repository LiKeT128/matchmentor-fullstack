
import urllib.request
import urllib.error

base_url = "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/"

candidates = [
    "rattletrap.png",
    "clockwerk.png",
    "furion.png",
    "natures_prophet.png",
    "zuus.png",
    "zeus.png",
    "nevermore.png",
    "shadow_fiend.png"
]

print("Checking CDN URLs...")
for c in candidates:
    url = base_url + c
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"[FOUND] {c}")
    except urllib.error.HTTPError as e:
        print(f"[MISSING] {c} ({e.code})")
    except Exception as e:
        print(f"[ERROR] {c}: {e}")
