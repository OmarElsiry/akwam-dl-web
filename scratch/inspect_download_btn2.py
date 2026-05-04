import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')

html = requests.get('https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6', headers={'User-Agent': 'Mozilla/5.0'}).text

match = re.search(r'<a[^>]*class=["\'][^"\']*download[^"\']*["\'][^>]*>.*?</a>', html, re.S)
if match:
    print("Found a.download:")
    print(match.group(0))
else:
    print("No a.download found")

# Look for any other elements with download in href or text
all_downloads = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?تحميل.*?</a>', html, re.S)
print("Other download links (by text 'تحميل'):")
for d in all_downloads:
    print(d)
