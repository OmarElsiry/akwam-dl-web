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
result = client.scrape(url, formats=['markdown'])
markdown = result.markdown or ''

# The new regex we put in the code
pattern = r'\[(?:[^]]*)\*\*([^*\n]+)\*\*(?:\s*[^]]*)\]\((https?://[^)\s\"]+)'

matches = re.findall(pattern, markdown)
print(f"Total matches found: {len(matches)}")

for name, link in matches:
    if 'batman-caped-crusader' in link.lower():
        print(f"FOUND: {name} -> {link}")

# If zero found, let's see what the markdown looks like around Batman
if not any('batman-caped-crusader' in l.lower() for n, l in matches):
    print("\n--- Searching for 'Batman' raw lines ---")
    lines = markdown.splitlines()
    for line in lines:
        if 'Batman' in line:
            print(f"LINE: {line}")
