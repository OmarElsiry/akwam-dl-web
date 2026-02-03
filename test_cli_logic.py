import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

# Test with CLI logic
short_url = "http://go.ak.sv/link/109981"

print("=== TESTING CLI LOGIC ===")
print(f"Starting with: {short_url}\n")

# Step 1
resp = requests.get(short_url, headers=HEADERS)
print(f"Step 1 - After first GET:")
print(f"  Final URL: {resp.url}")
print(f"  Status: {resp.status_code}")

# Look for download link in page
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
match = re.search(RGX_SHORTEN_URL, resp.text)
if match:
    target = 'https://' + match.group(1)
    print(f"  Found download link: {target}\n")
else:
    print(f"  No download link found in page\n")
    # Check if already redirected
    if "/download/" in resp.url:
        target = resp.url
        print(f"  Using redirected URL: {target}\n")
    else:
        print("  FAILED - No download link found")
        exit(1)

# Step 2
print(f"Step 2 - Getting download page:")
resp = requests.get(target, headers=HEADERS)
print(f"  Final URL: {resp.url}")
print(f"  Status: {resp.status_code}")

if resp.url != target:
    print(f"  Detected redirect, following...")
    resp = requests.get(resp.url, headers=HEADERS)
    print(f"  New URL: {resp.url}")

# Look for direct link
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
match = re.search(RGX_DIRECT_URL, resp.text)
if match:
    final = match.group(1)
    if not final.startswith('http'):
        final = 'https://' + final
    print(f"\n✅ FINAL DIRECT URL: {final}")
    
    # Save to file for easy viewing
    with open('test_result.txt', 'w') as f:
        f.write(f"FINAL DIRECT URL: {final}\n")
else:
    print(f"\n❌ FAILED - No direct URL found")
    # Save page for debugging
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print("  Saved page to debug_page.html")
