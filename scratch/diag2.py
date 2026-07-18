"""Check if server names exist in page, and dump raw HTML snippet."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from firecrawl import Firecrawl

app = Firecrawl(api_key='fc-186b4e776b4042dfa4043a97c4985cc9')
url = 'https://tv8.egydead.live/avatar-3-fire-and-ash-2025-1080p-web-dl/'
result = app.scrape(url, formats=['html'])
html = result.html or ''

# Search for known server names
for name in ['forafile', 'dood', 'mixdrop', 'earnvids', 'streamhg', 'vidhide', 'uqload', 'ok.ru', 'stream']:
    idx = html.lower().find(name)
    if idx > -1:
        print(f'Found [{name}] at pos {idx}:')
        print(html[max(0, idx-80):idx+300])
        print('---')

# Also dump the raw HTML around the watch button area
for kw in ['\u0645\u0634\u0627\u0647\u062f\u0647', 'watch', 'play', 'btn']:
    idx = html.lower().find(kw.lower())
    if idx > -1:
        print(f'Keyword [{kw}] at {idx}:')
        print(html[max(0, idx-40):idx+400])
        print('===')
        break

print('TOTAL HTML chars:', len(html))
