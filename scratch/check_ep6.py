import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {'User-Agent': 'Mozilla/5.0'}
ep6_url = 'https://akwam.com.co/episode/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6'
html = requests.get(ep6_url, headers=HEADERS).text

matches = re.findall(r'<a[^>]+href=["\'](https://go\.akwam\.com\.co/link/\d+)["\'][^>]*>.*?<span[^>]*>(.*?)</span>', html, re.S)
print("Episode 6 Qualities:")
for link, quality in matches:
    print(f"  {quality.strip()} -> {link}")
    
    # check if download page has link
    link_id = link.split('/')[-1]
    link_page = requests.get(link, headers=HEADERS).text
    dl_pages = re.findall(r'<a[^>]+href="(https://akwam\.com\.co/download/[^"]+)"', link_page)
    if dl_pages:
        dl_html = requests.get(dl_pages[0], headers=HEADERS).text
        RGX = re.compile(r"""\$\s*\(\s*['"]a\.download['"]\s*\)\s*\.attr\s*\(\s*['"]href['"]\s*,\s*['"]([^'"]+)['"]\s*\)""")
        m = RGX.search(dl_html)
        if m and m.group(1).strip():
            print(f"    [OK] Found direct link for {quality.strip()}")
        else:
            print(f"    [EMPTY] No direct link for {quality.strip()}")
