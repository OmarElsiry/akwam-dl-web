import requests
import json

BASE_URL = "http://localhost:8000"

def test_series(series_name):
    r = requests.get(f"{BASE_URL}/api/search", params={"q": series_name, "type": "series"})
    data = r.json()
    first_result = data.get('results', data)[0]
    link = first_result.get('url', first_result.get('link'))
    
    r = requests.post(f"{BASE_URL}/api/episodes", json={"url": link})
    episodes = r.json()['episodes']
    ep_to_test = episodes[min(2, len(episodes)-1)] # Try episode 3
    ep_link = ep_to_test.get('url', ep_to_test.get('link'))
    
    r = requests.post(f"{BASE_URL}/api/qualities", json={"url": ep_link})
    qualities = r.json()['qualities']
    quality_to_test = qualities[0]
    q_link = quality_to_test.get('url', quality_to_test.get('link'))
    
    r = requests.post(f"{BASE_URL}/api/resolve", json={"url": q_link})
    resolve_data = r.json()
    if 'url' not in resolve_data:
        return {
            "series": series_name,
            "error": "No 'url' in resolve response",
            "resolve_data": resolve_data,
            "q_link": q_link
        }
    
    link_id_url = resolve_data['url']
    
    r = requests.get(f"{BASE_URL}/api/akwam-resolve-stream", params={"link_id": link_id_url})
    
    return {
        "series": series_name,
        "ep_link": ep_link,
        "q_link": q_link,
        "link_id_url": link_id_url,
        "resolve_status": r.status_code,
        "resolve_body": r.json() if r.status_code == 200 else r.text
    }

results = []
try:
    results.append(test_series("اللعبة"))
except Exception as e:
    results.append({"error_le3ba": str(e)})

try:
    results.append(test_series("bloodhounds"))
except Exception as e:
    results.append({"error_bloodhounds": str(e)})

with open("compare_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
