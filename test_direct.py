import requests
import re
r2 = requests.get('https://akwam.com.co/download/153885/9364/merry-little-batman-%D9%85%D8%AF%D8%A8%D9%84%D8%AC-1', allow_redirects=True)
print(r2.url)
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.[\w.-]+/download/.*?)"'
m2 = re.search(RGX_DIRECT_URL, r2.text)
if m2:
    print("Match:", m2.group(1))
else:
    print("No direct URL matched in HTML.")
    with open('direct_page.html', 'w', encoding='utf-8') as f:
        f.write(r2.text)
