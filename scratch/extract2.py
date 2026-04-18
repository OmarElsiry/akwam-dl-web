from bs4 import BeautifulSoup
import re

html = open('correct_egy.html', 'r', encoding='utf-8', errors='ignore').read()
soup = BeautifulSoup(html, 'html.parser')

print("=== SERVER BUTTONS ===")
for li in soup.select('li[data-link]'):
    print(f"Data-Link: {li.get('data-link')} Text: {li.text.strip()}")

print("\n=== DOWNLOAD LINKS ===")
for a in soup.find_all('a'):
    href = a.get('href', '')
    text = a.text.strip()
    if 'download' in href.lower() or 'تحميل' in text or 'dl' in href.lower() or 'quality' in href.lower() or '1080p' in text or '720p' in text or '480p' in text and 'tv8.egydead.live/video' not in href:
         res = f"Text: {text} | Href: {href}"
         print(res.encode('ascii','ignore').decode())

print("\n=== All Qualities ===")
for div in soup.select('div[class*="quality"], div[class*="download"]'):
    print(div.get('class'))
