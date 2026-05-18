import requests

BASE_URL = "http://localhost:8000"

def test_series(series_name):
    # Search
    r = requests.get(f"{BASE_URL}/api/search", params={"q": series_name, "type": "series"})
    data = r.json()
    first_result = data['results'][0]
    link_key = 'url' if 'url' in first_result else 'link'
    
    # Get episodes
    r = requests.post(f"{BASE_URL}/api/episodes", json={"url": first_result[link_key]})
    episodes = r.json()['episodes']
    ep_to_test = episodes[min(2, len(episodes)-1)] # Try to get episode 3 (index 2) or the last one
    
    ep_link_key = 'url' if 'url' in ep_to_test else 'link'
    
    # Get qualities
    r = requests.post(f"{BASE_URL}/api/qualities", json={"url": ep_to_test[ep_link_key]})
    qualities = r.json()['qualities']
        
    quality_to_test = qualities[0]
    q_link_key = 'url' if 'url' in quality_to_test else 'link'
    
    # Resolve to get the go.akwam.com.co/link/ ID
    r = requests.post(f"{BASE_URL}/api/resolve", json={"url": quality_to_test[q_link_key]})
    link_id_url = r.json()['url']
    
    # Fast resolve stream
    r = requests.get(f"{BASE_URL}/api/akwam-resolve-stream", params={"link_id": link_id_url})
    
    res = {
        "series": series_name,
        "fast_resolve_status": r.status_code,
        "fast_resolve_json": r.json() if r.status_code == 200 else r.text
    }
    import json
    with open("compare_results.json", "a", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
        f.write("\n")

import os
if os.path.exists("compare_results.json"):
    os.remove("compare_results.json")

test_series("اللعبة")
test_series("bloodhounds")
