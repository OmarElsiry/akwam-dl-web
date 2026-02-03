import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

def debug_resolve(url):
    print(f"Resolving: {url}")
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status: {r.status_code}")
    print(f"Content Length: {len(r.text)}")
    
    # Save for inspection
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
    
    # Find next links
    links = re.findall(r'href=[\"\'](https?://.*?)[\"\']', r.text)
    print("\nAll links found:")
    for l in links[:20]:
        if 'ak.sv' in l or 'go.ak.sv' in l:
            print(f"- {l}")

if __name__ == "__main__":
    debug_resolve("http://go.ak.sv/watch/7057")
