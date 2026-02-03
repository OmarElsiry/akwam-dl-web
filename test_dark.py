import requests
import urllib.parse

BASE_URL = "https://akwam-dl-web-ul8s.vercel.app/api/akwam"

def test():
    print("--- TESTING DARK SERIES ---")
    # 1. Search Dark
    search = requests.get(f"{BASE_URL}?action=search&q=dark&type=series").json()
    print(f"Search found {len(search)} results.")
    
    # 2. Get episodes of the first 'Dark' result
    dark = next((s for s in search if "Dark" in s['title']), search[0])
    print(f"Selected: {dark['title']}")
    
    eps = requests.get(f"{BASE_URL}?action=episodes&url={urllib.parse.quote(dark['url'])}").json()
    print(f"Found {len(eps)} episodes.")
    
    # 3. Get quality for Episode 1
    ep1 = eps[0]
    print(f"Episode: {ep1['title']}")
    
    details = requests.get(f"{BASE_URL}?action=details&url={urllib.parse.quote(ep1['url'])}").json()
    print(f"Qualities available: {list(details.keys())}")
    
    if details:
        q = list(details.keys())[0]
        q_url = details[q]
        print(f"Resolving {q}: {q_url}")
        
        resolve = requests.get(f"{BASE_URL}?action=resolve&url={urllib.parse.quote(q_url)}").json()
        print(f"RESULT: {resolve}")

if __name__ == "__main__":
    test()
