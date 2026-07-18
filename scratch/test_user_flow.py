import requests
import json

BASE_URL = "http://localhost:8000"

r = requests.get(f"{BASE_URL}/api/search", params={"q": "bloodhound", "type": "series"})
data = r.json()

if not data.get('results'):
    exit(1)

link = data['results'][0]['url']
r = requests.post(f"{BASE_URL}/api/episodes", json={"url": link})
episodes = r.json().get('episodes', [])

ep3 = None
for ep in episodes:
    if '3' in ep.get('name', ''):
        ep3 = ep
        break

if not ep3:
    ep3 = episodes[-1]

r = requests.post(f"{BASE_URL}/api/qualities", json={"url": ep3['url']})

with open("scratch/bloodhound_user_flow.json", "w", encoding="utf-8") as f:
    json.dump({
        "search_link": link,
        "episode": ep3,
        "qualities": r.json()
    }, f, ensure_ascii=False, indent=2)
