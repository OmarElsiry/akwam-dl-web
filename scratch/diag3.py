"""Dump raw HTML to file so we can inspect the button structure."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from firecrawl import Firecrawl

app = Firecrawl(api_key='fc-186b4e776b4042dfa4043a97c4985cc9')
url = 'https://tv8.egydead.live/avatar-3-fire-and-ash-2025-1080p-web-dl/'
result = app.scrape(url, formats=['html'])
html = result.html or ''

with open('scratch/page_raw.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Saved {len(html)} chars to scratch/page_raw.html")

# Also try Firecrawl actions to click the watch button
print("\nNow trying with actions (click watch button)...")
try:
    # Try common EgyDead selectors
    result2 = app.scrape(url, formats=['html'], actions=[
        {"type": "wait", "milliseconds": 2000},
        {"type": "click", "selector": ".watchBtn, .watch-btn, a.btn-watch, .eps-toggle, .play-btn, [class*='watch']"},
        {"type": "wait", "milliseconds": 3000},
    ])
    html2 = result2.html or ''
    with open('scratch/page_after_click.html', 'w', encoding='utf-8') as f:
        f.write(html2)
    print(f"After-click HTML: {len(html2)} chars -> scratch/page_after_click.html")

    import re
    iframes2 = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html2, re.IGNORECASE)
    print(f"Iframes after click: {len(iframes2)}")
    for i in iframes2:
        print("  ", i[:150])
except Exception as e:
    print(f"Actions failed: {e}")
