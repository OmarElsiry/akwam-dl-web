import requests
import re

# Pre-compiled regex
RE_SHORTEN = re.compile(r'href="(https?://[^"]+?/download/[^"]+)"')
RE_DIRECT = re.compile(r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"')  # Fixed to match CLI

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

def resolve_link(short_url):
    if not short_url.startswith('http'):
        short_url = 'https://' + short_url
    
    print(f"[DEBUG] Starting with: {short_url}")
    
    # Step 1: Shortened Link -> Download Page
    resp = requests.get(short_url, headers=HEADERS)
    print(f"[DEBUG] Step 1 - Got response, status: {resp.status_code}")
    print(f"[DEBUG] Step 1 - Final URL: {resp.url}")
    
    # Intermediate link lookup
    match1 = RE_SHORTEN.search(resp.text)
    
    if match1:
        target = match1.group(1)
        print(f"[DEBUG] Step 1 - Found download link in page: {target}")
    elif "/download/" in resp.url:
        target = resp.url
        print(f"[DEBUG] Step 1 - Using redirected URL: {target}")
    else:
        print(f"[DEBUG] Step 1 - FAILED: No download link found")
        return None
        
    target = target.rstrip('"')
    if not target.startswith('http'): target = 'https://' + target
    
    print(f"[DEBUG] Step 1 - Target for Step 2: {target}")
    
    # Step 2: Download Page -> Final Direct Link
    print(f"[DEBUG] Step 2 - Fetching download page...")
    resp = requests.get(target, headers=HEADERS)
    print(f"[DEBUG] Step 2 - Got response, status: {resp.status_code}")
    print(f"[DEBUG] Step 2 - Final URL: {resp.url}")
    
    if resp.url != target:
        # Handle redirection just like the CLI script
        print(f"[DEBUG] Step 2 - Detected redirect, following...")
        resp = requests.get(resp.url, headers=HEADERS)
        print(f"[DEBUG] Step 2 - After redirect, URL: {resp.url}")
        
    # The key regex capturing alphanumeric hash links
    print(f"[DEBUG] Step 2 - Searching for direct download link...")
    match2 = RE_DIRECT.search(resp.text)
    
    if match2:
        final_url = match2.group(1).rstrip('"')
        print(f"[DEBUG] Step 2 - Found match: {final_url}")
        # Ensure protocol
        result = final_url if final_url.startswith('http') else 'https://' + final_url
        print(f"[DEBUG] Step 2 - Final result: {result}")
        return result
    else:
        print(f"[DEBUG] Step 2 - FAILED: No direct link found in page")
        # Save for debugging
        with open('step2_page.html', 'w', encoding='utf-8') as f:
            f.write(resp.text)
        print(f"[DEBUG] Saved page to step2_page.html")
        return None

# Test
result = resolve_link("http://go.ak.sv/link/109981")
print(f"\n{'='*60}")
print(f"FINAL RESULT: {result}")
print(f"{'='*60}")
