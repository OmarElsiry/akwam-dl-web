import requests
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_episodes(series_url):
    print(f"Fetching episodes: {series_url}")
    resp = requests.get(series_url, headers=HEADERS)
    resp.encoding = 'utf-8'
    
    # Pattern to catch absolute and relative links
    pattern = r'href="((?:https?://ak\.sv)?/episode/\d+/.*?)"'
    matches = re.findall(pattern, resp.text)
        
    episodes = []
    seen = set()
    for link in matches[::-1]:
        full_url = link if link.startswith('http') else f"https://ak.sv{link}"
        if full_url not in seen:
            seen.add(full_url)
            episodes.append(full_url)
    return episodes

if __name__ == "__main__":
    url = "https://ak.sv/series/67/breaking-bad-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84"
    res = fetch_episodes(url)
    print(f"Found {len(res)} episodes")
    print(json.dumps(res[:5], indent=4))
