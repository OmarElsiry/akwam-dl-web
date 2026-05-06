"""
The CDN always returns 403 from Python requests.
Let's check if the mp4 URL actually works from a REAL browser.
We'll use the proxy-stream approach but test with the download page
to understand the actual mechanism.
"""
import requests, re, time

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
})

# Step 1: Visit the /link/ page
link_url = 'https://go.akwam.com.co/link/143994'
print(f"Step 1: GET {link_url}")
r1 = session.get(link_url, timeout=30)
print(f"  Status: {r1.status_code}, URL: {r1.url[:80]}")

# Get /download/ URLs
dl_links = list(dict.fromkeys(re.findall(r'href="(https?://[^"]+/download/[^"]+)"', r1.text)))
print(f"  Download links: {len(dl_links)}")
for i, dl in enumerate(dl_links):
    print(f"    {i}: {dl[:80]}...")

# Step 2: Visit the download page (this sets up the token on the server)
print(f"\nStep 2: GET {dl_links[0][:60]}...")
r2 = session.get(dl_links[0], timeout=30)
print(f"  Status: {r2.status_code}")

# Extract mp4 URL
mp4_urls = re.findall(r'href=["\']([^"\']+\.mp4)["\']', r2.text)
mp4_url = mp4_urls[0] if mp4_urls else None
print(f"  MP4 URL: {mp4_url}")

# Look for any AJAX/POST that might "activate" the download
# Check for data-token, csrf, or any hidden form
tokens = re.findall(r'name=["\']_token["\'].*?value=["\']([^"\']+)', r2.text)
csrf = re.findall(r'meta.*?csrf.*?content=["\']([^"\']+)', r2.text)
print(f"  _token fields: {tokens}")
print(f"  CSRF metas: {csrf}")

# Look for JS that sends a request to "activate" the download
scripts = re.findall(r'<script[^>]*>(.*?)</script>', r2.text, re.DOTALL)
for i, s in enumerate(scripts):
    s_clean = s.strip()
    if not s_clean:
        continue
    if any(kw in s_clean.lower() for kw in ['download', 'timer', 'settimeout', 'ajax', 'fetch', 'xmlhttp', 'post']):
        print(f"\n  === Script {i} ===")
        print(f"  {s_clean[:800]}")

# Step 3: Maybe the timer activates a server endpoint? Let's wait and try
print(f"\nStep 3: Waiting 3 seconds (countdown simulation)...")
time.sleep(3)

# Try again after waiting
print("  Trying mp4 after wait...")
r3 = session.get(mp4_url, stream=True, timeout=15, headers={'Referer': dl_links[0]})
print(f"  Status: {r3.status_code}, CT: {r3.headers.get('content-type')}")
r3.close()

# Step 4: Check if there's a different domain/server pair in download links
# Maybe one of the mirror servers works differently
print("\nStep 4: Trying alternate servers...")
for i, dl in enumerate(dl_links[1:], 1):
    print(f"\n  Server {i}: {dl[:60]}...")
    r = session.get(dl, timeout=30, allow_redirects=True)
    print(f"  Status: {r.status_code}, Final URL: {r.url[:80]}")
    
    # Check if this server redirected to the file directly
    ct = r.headers.get('content-type', '')
    if 'video' in ct or 'octet-stream' in ct:
        print(f"  ** DIRECT VIDEO! CT: {ct}")
        break
    
    # Check for mp4 in this page
    alt_mp4 = re.findall(r'href=["\']([^"\']+\.mp4)["\']', r.text)
    if alt_mp4:
        print(f"  MP4: {alt_mp4[0][:80]}")
        time.sleep(3)
        r_alt = session.get(alt_mp4[0], stream=True, timeout=15, headers={'Referer': dl})
        print(f"  After wait, Status: {r_alt.status_code}, CT: {r_alt.headers.get('content-type')}")
        if r_alt.status_code == 200:
            chunk = next(r_alt.iter_content(1024), None)
            print(f"  Chunk: {len(chunk)} bytes") if chunk else print("  No data!")
        r_alt.close()
