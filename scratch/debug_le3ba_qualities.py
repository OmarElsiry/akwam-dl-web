import requests
import json

BASE_URL = "http://localhost:8000"

r = requests.get(f"{BASE_URL}/api/search", params={"q": "اللعبة", "type": "series"})
series = r.json().get('results', [])[0]
link = series.get('url', series.get('link'))
r = requests.post(f"{BASE_URL}/api/episodes", json={"url": link})
ep = r.json().get('episodes', [])[0]
ep_link = ep.get('url', ep.get('link'))
r = requests.post(f"{BASE_URL}/api/qualities", json={"url": ep_link})

print(json.dumps(r.json(), indent=2))
