"""Test exact firecrawl click on the button."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from firecrawl import Firecrawl
from bs4 import BeautifulSoup

app = Firecrawl(api_key='fc-186b4e776b4042dfa4043a97c4985cc9')
url = 'https://tv8.egydead.live/avatar-3-fire-and-ash-2025-1080p-web-dl/'

print("Sending scrape request with click action on .watchNow button...")
try:
    result = app.scrape(url, formats=['html'], actions=[
        {"type": "wait", "milliseconds": 2000},
        {"type": "click", "selector": ".watchNow button"},
        {"type": "wait", "milliseconds": 5000},
    ])
    html = result.html or ''
    print(f"Success. Returned HTML length: {len(html)}")
    
    with open('scratch/page_clicked.html', 'w', encoding='utf-8') as f:
        f.write(html)
        
    soup = BeautifulSoup(html, 'html.parser')
    
    iframes = soup.find_all('iframe')
    print(f"Iframes found: {len(iframes)}")
    for iframe in iframes:
        print(f"  - {iframe.get('src')}")
        
    servers = soup.find_all('ul', class_='serversList')
    if servers:
        print("Found serversList!")
        for li in servers[0].find_all('li'):
            print(f"  {li.text.strip()}")
            
    # look for any li containing known server names
    for li in soup.find_all('li'):
        if any(name in li.text for name in ['Forafile', 'DoodStream', 'Mixdrop', 'StreamHG', 'Vidhide']):
            print(f"Found server item: {li.text.strip()} (class: {li.get('class')}) [data-url: {li.get('data-url')}] [data-targer: {li.get('data-targer')}]")
            
except Exception as e:
    print(f"Failed: {e}")
