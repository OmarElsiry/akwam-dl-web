import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_movie_page(url):
    print(f"Checking movie page: {url}")
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    
    # Check for quality links
    pattern = r'href="(https?://[^"]+?/link/\d+)"'
    matches = re.findall(pattern, resp.text)
    print(f"Found {len(matches)} link/ URLs")
    for m in matches:
        print(f"  - {m}")

    # Check for different link patterns
    pattern2 = r'href="(https?://[^"]+?/download/[^"]+)"'
    matches2 = re.findall(pattern2, resp.text)
    print(f"Found {len(matches2)} download/ URLs")
    for m in matches2:
        print(f"  - {m}")

if __name__ == "__main__":
    check_movie_page("https://ak.sv/movie/6094/the-batman-1")
