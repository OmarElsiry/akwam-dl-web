import requests
import re

url = "https://go.akwam.com.co/link/143994"
print(f"Fetching link page: {url}")
r1 = requests.get(url)
html1 = r1.text

raw_links = re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)
seen = set()
dl_links = []
for u in raw_links:
    if u not in seen:
        seen.add(u)
        dl_links.append(u)

print(f"Found download pages: {dl_links}")

if dl_links:
    dl_url = dl_links[0]
    print(f"Fetching download page: {dl_url}")
    r2 = requests.get(dl_url, allow_redirects=True, timeout=20)
    html2 = r2.text
    
    with open('scratch/bloodhounds_dl_page.html', 'w', encoding='utf-8') as f:
        f.write(html2)
    
    mp4_matches = re.findall(r'href=["\']([^"\']+\.mp4)["\']', html2)
    mkv_matches = re.findall(r'href=["\']([^"\']+\.mkv)["\']', html2)
    print(f"mp4 matches: {mp4_matches}")
    print(f"mkv matches: {mkv_matches}")
    
    # print all downet links
    downet_links = re.findall(r'href=["\']([^"\']+)["\']', html2)
    downet = [x for x in downet_links if 'downet' in x]
    print(f"Downet links: {downet}")
