"""Diagnostic: inspect what an EgyDead movie page contains."""
import re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from firecrawl import Firecrawl

app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")

# Use a movie we KNOW exists from the search results
url = "https://tv8.egydead.live/avatar-3-fire-and-ash-2025-1080p-web-dl/"
print(f"Scraping: {url}\n")

# --- 1. Basic scrape (no actions) ------------------------------------------------
result = app.scrape(url, formats=['html', 'markdown'])
html = result.html or ''
md   = result.markdown or ''

print(f"HTML length: {len(html)} chars")
print(f"MD  length : {len(md)} chars\n")

# --- 2. iframes ------------------------------------------------------------------
iframes = re.findall(r'<iframe[^>]+>', html, re.IGNORECASE)
print(f"=== IFRAMES ({len(iframes)}) ===")
for f in iframes:
    print("  ", f[:200])

# --- 3. data-src / data-link / data-video attrs ----------------------------------
data_attrs = re.findall(r'data-(?:src|link|video|iframe|url)=["\']([^"\']+)["\']', html, re.IGNORECASE)
print(f"\n=== data-* video attrs ({len(data_attrs)}) ===")
for d in data_attrs[:10]:
    print("  ", d[:150])

# --- 4. script tags that contain http links ONLY (likely embeds) -----------------
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
print(f"\n=== SCRIPT blocks with 'src'/'embed'/'player' ({len(scripts)} total) ===")
for i, s in enumerate(scripts):
    if any(kw in s.lower() for kw in ['src', 'embed', 'player', 'video', 'stream']):
        snippet = s.strip()[:600]
        print(f"  -- Script {i} --")
        print("  ", snippet)
        print()

# --- 5. All <a> hrefs that look like external video/server links -----------------
links_raw = re.findall(r"href=[\"']([^\"']+)[\"']", html, re.IGNORECASE)
print(f"\n=== External-looking hrefs ({len(links_raw)}) ===")
for href in links_raw:
    if href.startswith('http') and 'egydead' not in href and 'wp-' not in href:
        print("  ", href[:150])

# --- 6. Look for encoded base64 or JSON blobs with video data -------------------
b64_blobs = re.findall(r'["\']([A-Za-z0-9+/=]{60,})["\']', html)
print(f"\n=== Possible base64 blobs ({len(b64_blobs)}) ===")
for b in b64_blobs[:3]:
    print("  ", b[:80], "...")
