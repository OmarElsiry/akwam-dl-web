import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_page(url):
    print(f"Checking page: {url}")
    resp = requests.get(url, headers=HEADERS)
    print(f"Status: {resp.status_code}")
    
    # Save a snippet
    with open("page_snippet.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    
    # Check for direct links
    pattern = r'href="(https?://[^"]+?/download/[^"]+)"'
    matches = re.findall(pattern, resp.text)
    print(f"Found {len(matches)} direct links in href")
    for m in matches:
        print(f"  - {m}")
        
    # Check for script links
    pattern_script = r'(https?://[^"]+?/download/[^"]+)'
    matches_script = re.findall(pattern_script, resp.text)
    print(f"Found {len(matches_script)} potential links in scripts/text")
    for m in matches_script[:5]:
        print(f"  - {m}")

if __name__ == "__main__":
    # From previous test
    check_page("http://link.akwam.bz/download/624953930499e/")
