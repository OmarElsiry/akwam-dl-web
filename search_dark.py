from requests import get
import re

def search_series(query):
    base_url = get('https://ak.sv/').url.rstrip('/')
    search_url = f"{base_url}/search?q={query.replace(' ', '+')}&section=series&page=1"
    print(f"Searching: {search_url}")
    res = get(search_url)
    pattern = rf'({base_url}/series/\d+/.*?)"'
    matches = re.findall(pattern, res.text)
    results = {}
    for match in matches:
        name = match.split('/')[-1].replace('-', ' ').title()
        results[name] = match
    return results

if __name__ == "__main__":
    results = search_series("dark")
    print("Results for 'dark':")
    for n, u in results.items():
        print(f"  {n}: {u}")
    
    results2 = search_series("dark season")
    print("\nResults for 'dark season':")
    for n, u in results2.items():
        print(f"  {n}: {u}")
