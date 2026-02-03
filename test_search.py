import requests
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def search(query):
    url = f"https://ak.sv/search?q={query}"
    print(f"Searching: {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    
    # Looking for /movie/123/title or /series/123/title
    pattern = r'href="(https?://ak\.sv/(?:movie|series)/\d+/[^"]+)"'
    matches = re.findall(pattern, resp.text)
    
    results = []
    seen = set()
    for link in matches:
        if link not in seen:
            seen.add(link)
            results.append(link)
    return results

if __name__ == "__main__":
    res = search("breaking bad")
    print(json.dumps(res, indent=4))
