"""
Debug step 4 — resolve_direct_url for Bloodhounds ep1
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')
from api.akwam_api import safe_get, RGX_SHORTEN_URL, RGX_DIRECT_URL

HTTP = 'https://'
link_id = 'go.akwam.com.co/link/143999'

print(f"[INPUT] link_id = {link_id}")
url1 = HTTP + link_id
print(f"\n-- Step A: GET {url1}")
r1 = safe_get(url1)
print(f"   Status: {r1.status_code}  Final URL: {r1.url}")

html1 = r1.content.decode('utf-8', errors='replace')

# Save for inspection
open('scratch/debug_step4_a.html', 'w', encoding='utf-8').write(html1)
print(f"   Saved html to scratch/debug_step4_a.html  (len={len(html1)})")

# Try RGX_SHORTEN_URL
m1 = re.search(RGX_SHORTEN_URL, html1)
print(f"\n-- RGX_SHORTEN_URL match: {m1}")

# Also try broader patterns
broad_dl = re.findall(r'href=\"(https?://[^\"]+/download/[^\"]+)\"', html1)
print(f"   Broad /download/ hrefs: {broad_dl[:5]}")

broad_all_links = re.findall(r'href=\"(https?://[^\"]{10,80})\"', html1)
print(f"   All hrefs (first 10): {broad_all_links[:10]}")

if m1:
    short_url = HTTP + m1.group(1)
    print(f"\n-- Step B: GET {short_url}")
    r2 = safe_get(short_url)
    print(f"   Status: {r2.status_code}  Final URL: {r2.url}")
    html2 = r2.content.decode('utf-8', errors='replace')
    open('scratch/debug_step4_b.html', 'w', encoding='utf-8').write(html2)
    print(f"   Saved html to scratch/debug_step4_b.html  (len={len(html2)})")

    m2 = re.search(RGX_DIRECT_URL, html2)
    print(f"\n-- RGX_DIRECT_URL match: {m2}")
    
    # Broader: find any anchor with download attribute
    dl_links = re.findall(r'href=\"(https?://[^\"]+)\"[^>]*download', html2)
    print(f"   Anchors with 'download': {dl_links[:5]}")
    
    # find mp4 links
    mp4_links = re.findall(r'(https?://[^\s\"\'<>]+\.mp4[^\s\"\'<>]*)', html2)
    print(f"   .mp4 links: {mp4_links[:5]}")
else:
    print("\n[FAIL] RGX_SHORTEN_URL matched nothing in step A page")
    # Print a snippet around 'download' if present
    for kw in ['download', 'btn', 'link', 'href']:
        idxs = [m.start() for m in re.finditer(kw, html1, re.I)]
        if idxs:
            s = idxs[0]
            print(f"\n   Snippet around first '{kw}': ...{html1[max(0,s-100):s+200]}...")
            break
