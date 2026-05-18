import requests
import json

BASE_URL = "http://localhost:8000"

# Search for bloodhounds
r = requests.get(f"{BASE_URL}/api/search", params={"q": "bloodhounds", "type": "series"})
data = r.json()
bloodhounds_res = [res for res in data.get('results', []) if 'bloodhound' in res.get('name', '').lower() or 'bloodhound' in res.get('title', '').lower()]

if not bloodhounds_res:
    series = data.get('results', [])[0]
else:
    series = bloodhounds_res[0]

link = series.get('url', series.get('link'))
r = requests.post(f"{BASE_URL}/api/episodes", json={"url": link})
episodes = r.json().get('episodes', [])
ep3 = episodes[0] # Just take first one
for ep in episodes:
    if '3' in ep.get('name', '') or '3' in ep.get('title', ''):
        ep3 = ep
        break

ep_link = ep3.get('url', ep3.get('link'))
r = requests.post(f"{BASE_URL}/api/qualities", json={"url": ep_link})

res = {
    "series_link": link,
    "ep_link": ep_link,
    "qualities": r.json()
}

with open("scratch/bloodhounds_qualities.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
