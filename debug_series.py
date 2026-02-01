import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def debug_series(url):
    print(f"Fetching Series Page: {url}")
    resp = requests.get(url, headers=HEADERS)
    print(f"Status: {resp.status_code}")
    
    # Try different patterns for episodes
    patterns = [
        r'href="(https?://ak\.sv/episode/\d+/.*?)"',
        r'href="(/episode/\d+/.*?)"',
        r'class="episode-item".*?href="(.*?)"',
        r'\/episode\/\d+\/.*?"'
    ]
    
    for p in patterns:
        matches = re.findall(p, resp.text)
        print(f"Pattern `{p}` found {len(matches)} matches.")
        if matches:
            print("First 3 matches:", matches[:3])

if __name__ == "__main__":
    # Standard Akwam series URL structure
    debug_series("https://ak.sv/series/596/suits-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%AA%D8%A7%D8%B3%D8%B9")
