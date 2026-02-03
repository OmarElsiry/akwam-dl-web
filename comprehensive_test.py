import requests
import time
import json

BASE_URL = "https://akwam-dl-web-ul8s.vercel.app/api/akwam"

def test_action(name, params):
    print(f"\n--- Testing {name} ---")
    start = time.time()
    try:
        r = requests.get(BASE_URL, params=params, timeout=60)
        end = time.time()
        print(f"Status: {r.status_code} | Time: {end-start:.2f}s")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"Results count: {len(data)}")
                for item in data[:3]:
                    print(f" - {json.dumps(item)}")
            else:
                print(f"Result: {json.dumps(data, indent=2)}")
            return data
    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    # 1. Movie Search & Resolve
    print("Step 1: Movie")
    movie_search = test_action("Movie Search", {"action": "search", "q": "The Batman", "type": "movie"})
    if movie_search:
        movie_url = movie_search[0]['url']
        quals = test_action("Movie Qualities", {"action": "details", "url": movie_url})
        if quals:
            q_url = quals.get('720p') or list(quals.values())[0]
            test_action("Movie Resolve", {"action": "resolve", "url": q_url})

    # 2. Episode Resolve
    print("\nStep 2: Single Episode")
    ep_url = "https://ak.sv/episode/781/granite-state"
    quals = test_action("Episode Qualities", {"action": "details", "url": ep_url})
    if quals:
        q_url = quals.get('720p') or list(quals.values())[0]
        test_action("Episode Resolve", {"action": "resolve", "url": q_url})

    # 3. Batch Resolve
    print("\nStep 3: Batch Resolve (Season)")
    series_url = "https://ak.sv/series/67/breaking-bad-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84"
    test_action("Batch Resolve", {"action": "batch", "url": series_url})
