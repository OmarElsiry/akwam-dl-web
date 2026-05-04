from firecrawl import Firecrawl
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")

print("Checking Akwam Episode 6...")
url = "https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6"

scrape_result = app.scrape(url, formats=['html'])

if hasattr(scrape_result, 'html'):
    html = scrape_result.html
elif isinstance(scrape_result, dict):
    html = scrape_result.get('html', '')
else:
    html = str(scrape_result)

print(f"Got HTML, length: {len(html)}")

import re
match = re.search(r'<a[^>]*class=["\'][^"\']*download[^"\']*["\'][^>]*href=["\']([^"\']+)["\']', html, re.S)
if match:
    print("Found direct download link:", match.group(1))
else:
    print("No a.download with href found.")
    
    with open('scratch/fc_ep6_dump.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Dumped HTML to scratch/fc_ep6_dump.html")
