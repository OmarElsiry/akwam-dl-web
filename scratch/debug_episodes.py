import sys
import re
import os
from firecrawl import Firecrawl

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FIRECRAWL_API_KEY = "fc-186b4e776b4042dfa4043a97c4985cc9"

client = Firecrawl(api_key=FIRECRAWL_API_KEY)
url = 'https://tv8.egydead.live/season/batman-caped-crusader-season-1/'

print(f"Scraping: {url}")
result = client.scrape(url, formats=['markdown', 'html'])
markdown = result.markdown or ''
html = result.html or ''

# 1. Check for episode links in markdown
pattern = r'\*\*([^*\n]+)\*\*[^\]]*\]\((https?://[^)\s"]+)'
matches = re.findalpushl(pattern, markdown)
print(f"Matches found in markdown (Pattern 1): {len(matches)}")
for title, link in matches[:10]:
    if '/episode/' in link:
        print(f"  - [EP] {title}: {link}")
    else:
        print(f"  - [OTHER] {title}: {link}")

# 2. Check for episode links in HTML
html_matches = re.findall(r'href=["\'](https?://[^"\']+/episode/[^"\']+)["\']', html)
print(f"Matches found in HTML (href contains /episode/): {len(html_matches)}")
for link in html_matches[:10]:
    print(f"  - {link}")

# 3. Check for the title pattern we used in EgyDeadAPI._parse_links_by_type
# Pattern: r'\*\*([^*\n]+)\*\*[^\]]*\]\((https?://[^)\s"]+)'
# URL Filter: '/episode/'
items = []
seen = set()
for title, link in re.findall(pattern, markdown):
    link = link.rstrip('/') + '/'
    if link not in seen and '/episode/' in link:
        seen.add(link)
        items.append({'name': title.strip(), 'url': link})

print(f"EgyDeadAPI style parser found: {len(items)} episodes")

# 4. Dump a snippet of markdown around where we expect episodes
idx = markdown.lower().find('episode')
if idx == -1:
    idx = markdown.lower().find('الحلقة')
if idx != -1:
    print("\n--- Markdown Snippet ---")
    print(markdown[max(0, idx-200):idx+500])
    print("------------------------\n")
else:
    print("Could not find 'episode' or 'الحلقة' in markdown.")

with open('scratch/debug_ep_output.md', 'w', encoding='utf-8') as f:
    f.write(markdown)
