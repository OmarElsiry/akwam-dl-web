import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Referer': 'https://go.ak.sv/'
}

def debug_resolve(url):
    print(f"Resolving: {url}")
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status: {r.status_code}")
    
    # Save for inspection
    with open('debug_page_final.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
    
    # Look for the final direct link. 
    # Usually it's in a script or a button with /download/
    links = re.findall(r'href=[\"\'](https?://.*?/download/.*?)[\"\']', r.text)
    print("\nDownload links found:")
    for l in links:
        print(f"- {l}")
    
    # Check for window.location
    locs = re.findall(r'window\.location\s*=\s*[\"\'](.*?)[\"\']', r.text)
    print("\nJS Redirects:")
    for l in locs:
        print(f"- {l}")

if __name__ == "__main__":
    debug_resolve("https://ak.sv/watch/7057/562/inception-1")
