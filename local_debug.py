import requests
import re
import json
import time

# Pre-compiled regex (EXACTLY from api/index.py)
RE_SHORTEN = re.compile(r'href="(https?://[^"]+?/download/[^"]+)"')
RE_DIRECT = re.compile(r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"')
RE_LINK = re.compile(r'href="(https?://[^"]+?/link/\d+)"')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

def resolve_link(short_url):
    print(f"Resolving: {short_url}")
    start = time.time()
    try:
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
        
        # Step 1
        resp = requests.get(short_url, headers=HEADERS, timeout=10)
        print(f"Step 1 Done ({time.time()-start:.2f}s). URL: {resp.url}")
        
        match1 = RE_SHORTEN.search(resp.text)
        if match1:
            target = match1.group(1)
        elif "/download/" in resp.url:
            target = resp.url
        else:
            print("No intermediate link found")
            return None
            
        target = target.rstrip('"')
        if not target.startswith('http'): target = 'https://' + target
        
        # Step 2
        print(f"Step 2 Request to: {target}")
        t2_start = time.time()
        resp = requests.get(target, headers=HEADERS, timeout=10)
        print(f"Step 2 Done ({time.time()-t2_start:.2f}s). URL: {resp.url}")
        
        if resp.url != target:
            print(f"Following redirect to: {resp.url}")
            resp = requests.get(resp.url, headers=HEADERS, timeout=10)
            
        match2 = RE_DIRECT.search(resp.text)
        if match2:
            final_url = match2.group(1).rstrip('"')
            res = final_url if final_url.startswith('http') else 'https://' + final_url
            print(f"Success! Found: {res}")
            return res
        else:
            print("No direct link found in Step 2 page")
            return None
    except Exception as e:
        print(f"Error in resolve_link: {e}")
        return None

if __name__ == "__main__":
    test_url = "http://go.ak.sv/link/109981"
    resolve_link(test_url)
