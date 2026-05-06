"""
Test: Use the exact same approach as main.py to resolve direct URLs
WITHOUT Playwright. Filter for the actual CDN URL (downet.net).
"""
import re
from requests import get

HTTP = 'https://'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

link_id = '143994'

# Step 1: GET /link/ page
print("Step 1: Getting /link/ page...")
r1 = get(f'{HTTP}go.akwam.com.co/link/{link_id}', headers=HEADERS, timeout=30)
shorten_matches = re.findall(RGX_SHORTEN_URL, r1.content.decode())
print(f"  Found {len(shorten_matches)} download links")

# Step 2: GET /download/ page
download_url = HTTP + shorten_matches[0]
print(f"Step 2: Getting download page...")
r2 = get(download_url, headers=HEADERS, timeout=30)

# Step 3: Parse ALL direct URLs
html = r2.content.decode()
all_matches = re.findall(RGX_DIRECT_URL, html)
print(f"Step 3: RGX_DIRECT_URL found {len(all_matches)} matches")

# Filter for actual CDN URLs (not akwam.com.co self-references)
cdn_urls = [m for m in all_matches if 'downet.net' in m or '.mp4' in m or '.mkv' in m]
print(f"  CDN URLs: {cdn_urls}")

if cdn_urls:
    dl_url = HTTP + cdn_urls[0]
    print(f"\nDIRECT URL: {dl_url}")
    
    # Test download
    print(f"\nStep 4: Testing download...")
    r3 = get(dl_url, headers=HEADERS, stream=True, timeout=15)
    print(f"  Status: {r3.status_code}")
    print(f"  Content-Type: {r3.headers.get('content-type')}")
    print(f"  Content-Length: {r3.headers.get('content-length')}")
    if r3.status_code == 200:
        chunk = next(r3.iter_content(1024), None)
        if chunk:
            print(f"  First 32 bytes: {chunk[:32].hex()}")
            print("  DOWNLOAD WORKS! No Playwright needed!")
    elif r3.status_code == 403:
        print("  403 - CDN still blocks this IP (datacenter)")
        print("  But the URL extraction works WITHOUT Playwright!")
        print("  This means we can skip the 10s Playwright overhead")
    r3.close()
else:
    print("  No CDN URLs found")
    # Show what we got
    for m in all_matches[:5]:
        print(f"    {m[:80]}")

# Also try the second download server (two.akw.cam)
alt_servers = [m for m in shorten_matches if 'akwam.com.co' not in m]
if alt_servers:
    print(f"\nStep 5: Trying alternate server: {alt_servers[0][:50]}...")
    r_alt = get(HTTP + alt_servers[0], headers=HEADERS, timeout=30)
    alt_matches = re.findall(RGX_DIRECT_URL, r_alt.content.decode())
    alt_cdn = [m for m in alt_matches if 'downet.net' in m or '.mp4' in m]
    if alt_cdn:
        alt_url = HTTP + alt_cdn[0]
        print(f"  Alt CDN URL: {alt_url}")
        r_test = get(alt_url, headers=HEADERS, stream=True, timeout=15)
        print(f"  Status: {r_test.status_code}, CT: {r_test.headers.get('content-type')}")
        r_test.close()
