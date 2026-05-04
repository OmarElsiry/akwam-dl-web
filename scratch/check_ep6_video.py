import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')

html = requests.get('https://akwam.com.co/episode/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6', headers={'User-Agent': 'Mozilla/5.0'}).text

srcs = re.findall(r'<source[^>]*src=["\']([^"\']+)["\']', html)
print("Video sources:")
for s in srcs:
    print(s)

iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\']', html)
print("\nIFrames:")
for i in iframes:
    print(i)
    
