"""Debug script to inspect Akwam episode page HTML for quality links."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import re
from requests import get

# Resolve Akwam URL
print(">> Resolving Akwam URL...")
base = get('https://ak.sv/').url
if base.endswith('/'):
    base = base[:-1]
print(f"   Base URL: {base}")

# Search for bloodhounds
search_url = base + '/search?q='
query = 'bloodh'
print(f"\n>> Searching for '{query}'...")
page = get(f'{search_url}{query}&section=series&page=1')
parsed = re.findall(rf'({base}/series/\d+/.*?)"', page.content.decode())
results = {
    url.split('/')[-1].replace('-', ' ').title(): url
    for url in reversed(parsed)
}
print(f"   Found {len(results)} results:")
for name, url in results.items():
    print(f"   - {name}: {url}")

if not results:
    print("No results found!")
    exit(1)

# Pick first result
first_name = list(results.keys())[0]
first_url = results[first_name]
print(f"\n>> Picking: {first_name}")

# Fetch episodes
print("\n>> Fetching episodes...")
page = get(first_url)
parsed = re.findall(rf'({base}/episode/\d+/.*?)"', page.content.decode())
episodes = {
    url.split('/')[-1].replace('-', ' ').title(): url
    for url in reversed(parsed)
}
print(f"   Found {len(episodes)} episodes")

if not episodes:
    print("No episodes found!")
    exit(1)

# Pick episode 6 (or first available)
ep_list = list(episodes.items())
ep_idx = min(5, len(ep_list) - 1)
ep_name, ep_url = ep_list[ep_idx]
print(f"\n>> Picking episode: {ep_name} -> {ep_url}")

# Fetch the episode page and inspect quality section
print("\n>> Fetching episode page...")
page = get(ep_url)
html = page.content.decode()

# Save full HTML for inspection
with open('scratch/episode_page.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("   Saved full HTML to scratch/episode_page.html")

# Check what the current regex finds
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_QUALITY_TAG = rf'tab-content quality.*?a href="{RGX_DL_URL}"'

html_no_newlines = html.replace('\n', '')
parsed_qualities = re.findall(RGX_QUALITY_TAG, html_no_newlines)
print(f"\n>> RGX_QUALITY_TAG matches: {len(parsed_qualities)}")
for p in parsed_qualities:
    print(f"   {p}")

# Check which quality labels appear in the page
for q in ['1080p', '720p', '480p', '360p', '240p']:
    if f'>{q}</' in html:
        print(f"   Quality label found in HTML: {q}")

# Try to find the quality section in raw HTML
print("\n>> Looking for quality-related HTML sections...")
# Search for 'tab-content' context
tab_matches = re.findall(r'tab-content.{0,500}', html_no_newlines)
print(f"   Found {len(tab_matches)} 'tab-content' sections")
for i, m in enumerate(tab_matches[:5]):
    print(f"\n   --- Section {i+1} (first 300 chars) ---")
    print(f"   {m[:300]}")

# Also try to find download links directly
print("\n>> Looking for /link/ URLs...")
link_matches = re.findall(r'href="(https?://[^"]*?/link/\d+[^"]*)"', html)
print(f"   Found {len(link_matches)} /link/ URLs:")
for lm in link_matches:
    print(f"   {lm}")

# Also look for quality + link patterns more broadly
print("\n>> Looking for quality near download links...")
quality_sections = re.findall(r'((?:1080|720|480|360|240)p.*?/link/\d+|/link/\d+.*?(?:1080|720|480|360|240)p)', html_no_newlines)
print(f"   Found {len(quality_sections)} quality+link patterns:")
for qs in quality_sections[:10]:
    print(f"   {qs[:200]}")
