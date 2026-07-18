import sys, re, requests

sys.stdout.reconfigure(encoding='utf-8')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_links(link_id):
    url = f"https://go.akwam.com.co/link/{link_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    links = []
    for match in re.finditer(r'<a[^>]+href="(https://akwam\.com\.co/download/[^"]+)"', r.text):
        links.append(match.group(1))
    return links

RGX_DOWNLOAD_HREF = re.compile(
    r"""\$\s*\(\s*['"]a\.download['"]\s*\)\s*\.attr\s*\(\s*['"]href['"]\s*,\s*['"]([^'"]+)['"]\s*\)""",
    re.IGNORECASE
)

for ep_num, link_id in [(8, 143999), (6, 143997), (5, 143996), (4, 143995), (3, 143994)]:
    print(f"\nEpisode {ep_num} (Link ID {link_id})")
    dl_pages = get_links(link_id)
    print(f"Found {len(dl_pages)} download pages.")
    
    for page in dl_pages:
        print(f"  Testing page: {page}")
        try:
            r = requests.get(page, headers=HEADERS, timeout=10)
            m = RGX_DOWNLOAD_HREF.search(r.text)
            if m:
                url = m.group(1).strip()
                if url:
                    print(f"    [OK] DIRECT URL: {url}")
                else:
                    print(f"    [EMPTY] URL is empty.")
            else:
                print(f"    [NO MATCH] No direct URL pattern found.")
        except Exception as e:
            print(f"    [ERROR] {e}")

