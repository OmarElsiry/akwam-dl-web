import requests

BASE_URL = "http://localhost:8000"

def test_series(series_name):
    print(f"Testing series: {series_name.encode('utf-8', errors='replace')}")
    # Search
    r = requests.get(f"{BASE_URL}/api/search", params={"q": series_name, "type": "series"})
    if r.status_code != 200:
        print(f"  Search failed: {r.text}")
        return
    
    data = r.json()
    if not data or 'results' not in data or not data['results']:
        print("  Empty search results")
        return
        
    first_result = data['results'][0]
    
    title_key = 'title' if 'title' in first_result else 'name'
    print(f"  Found: {first_result.get(title_key, '').encode('utf-8', errors='replace')} ({first_result.get('link', '')})")
    
    # Get episodes
    r = requests.post(f"{BASE_URL}/api/episodes", json={"url": first_result['link']})
    if r.status_code != 200 or not r.json().get('episodes'):
        print(f"  Episodes failed or empty: {r.text}")
        return
    
    episodes = r.json()['episodes']
    ep_to_test = episodes[min(2, len(episodes)-1)] # Try to get episode 3 (index 2) or the last one
    
    ep_title_key = 'title' if 'title' in ep_to_test else 'name'
    print(f"  Testing episode: {ep_to_test.get(ep_title_key, '').encode('utf-8', errors='replace')} ({ep_to_test['link']})")
    
    # Get qualities
    r = requests.post(f"{BASE_URL}/api/qualities", json={"url": ep_to_test['link']})
    if r.status_code != 200 or not r.json().get('qualities'):
        print(f"  Qualities failed or empty: {r.text}")
        return
    
    qualities = r.json()['qualities']
    print(f"  Found {len(qualities)} qualities")
    for q in qualities:
        print(f"    - {q['quality']}: {q['link']}")
        
    quality_to_test = qualities[0]
    print(f"  Resolving quality: {quality_to_test['quality']} ({quality_to_test['link']})")
    
    # Resolve to get the go.akwam.com.co/link/ ID
    r = requests.post(f"{BASE_URL}/api/resolve", json={"url": quality_to_test['link']})
    if r.status_code != 200 or not r.json().get('url'):
        print(f"  Resolve failed or empty: {r.text}")
        return
    
    link_id_url = r.json()['url']
    print(f"  Resolved link ID URL: {link_id_url}")
    
    # Fast resolve stream
    r = requests.get(f"{BASE_URL}/api/akwam-resolve-stream", params={"link_id": link_id_url})
    print(f"  Fast resolve status: {r.status_code}")
    if r.status_code == 200:
        print(f"  Fast resolve URL: {r.json().get('url')[:100]}...")
    else:
        print(f"  Fast resolve error: {r.text}")

print("==============================")
test_series("اللعبة")
print("\n==============================")
test_series("bloodhounds")
print("\n==============================")
