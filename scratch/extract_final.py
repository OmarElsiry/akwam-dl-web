"""
Akwam download URL extractor — final approach.
The real download URL is stored DIRECTLY in the HTML inside a setTimeout block:
  $('a.download').attr('href', 'https://s302d6.downet.net/download/...');
We just need to regex-extract it. No Playwright, no JS, no countdown wait.
"""
import sys, re, json, time
sys.stdout.reconfigure(encoding='utf-8')

import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
}

# Regex for the setTimeout block that sets the download href
# Matches: $('a.download').attr('href', 'URL');
RGX_DOWNLOAD_HREF = re.compile(
    r"""\$\s*\(\s*['"]a\.download['"]\s*\)\s*\.attr\s*\(\s*['"]href['"]\s*,\s*['"]([^'"]+)['"]\s*\)""",
    re.IGNORECASE
)

DOWNLOAD_PAGES = [
    ("Episode 8", "https://akwam.com.co/download/143999/78413/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-8"),
    ("Episode 7", "https://akwam.com.co/download/143998/78412/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-7"),
    ("Episode 6", "https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6"),
    ("Episode 5", "https://akwam.com.co/download/143996/78410/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-5"),
    ("Episode 4", "https://akwam.com.co/download/143995/78409/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-4"),
    ("Episode 3", "https://akwam.com.co/download/143994/78408/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-3"),
    ("Episode 2", "https://akwam.com.co/download/143993/78407/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-2"),
    ("Episode 1", "https://akwam.com.co/download/143992/78406/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-1"),
]


def extract_from_page(ep_name, page_url):
    print(f"[{ep_name}] Fetching...")
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=20)
        html = r.text
        
        m = RGX_DOWNLOAD_HREF.search(html)
        if m:
            url = m.group(1).strip()
            if url:  # non-empty
                print(f"  [OK] {url}")
                return url
            else:
                print(f"  [EMPTY] href is empty string — link may be expired or unavailable server-side")
                return None
        else:
            print(f"  [NO MATCH] Pattern not found in HTML (len={len(html)})")
            # Show the setTimeout block for debugging
            st = re.search(r'setTimeout.*?a\.download.*?\)', html, re.S)
            if st:
                print(f"  setTimeout snippet: {st.group(0)[:200]}")
            return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


results = []
for ep_name, page_url in DOWNLOAD_PAGES:
    direct_url = extract_from_page(ep_name, page_url)
    results.append({
        "episode": ep_name,
        "download_page": page_url,
        "direct_url": direct_url,
    })
    time.sleep(0.5)

print("\n" + "=" * 70)
print("FINAL RESULTS — Bloodhounds Season 1 (720p)")
print("=" * 70)
success = 0
for r in results:
    ep = r["episode"]
    url = r.get("direct_url")
    if url:
        success += 1
        print(f"[OK]   {ep}: {url}")
    else:
        print(f"[FAIL] {ep}: No direct URL in HTML (link expired or unavailable)")

print(f"\n{success}/{len(results)} direct links extracted")

with open("bloodhounds_direct_links_final.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n--- PLAIN DOWNLOAD LINKS ---")
for r in results:
    if r.get("direct_url"):
        print(r["direct_url"])
