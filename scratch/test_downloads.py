"""
Test the download extraction logic from egydead_api.py
against a real captured page (correct_egy.html).
"""
import re, sys, os

html = open(os.path.join('correct_egy.html'), encoding='utf-8', errors='ignore').read()

downloads = []
dl_block_match = re.search(
    r'<ul[^>]*class=["\'][^"\']*donwload-servers-list[^"\']*["\'][^>]*>(.*?)</ul>',
    html, re.DOTALL | re.IGNORECASE
)

if dl_block_match:
    for li_html in re.split(r'</li>', dl_block_match.group(1), flags=re.IGNORECASE):
        if not li_html.strip():
            continue
        name_m = re.search(
            r'<span[^>]*class=["\'][^"\']*ser-name[^"\']*["\'][^>]*>(.*?)</span>',
            li_html, re.IGNORECASE | re.DOTALL
        )
        qual_m = re.search(
            r'<div[^>]*class=["\'][^"\']*server-info[^"\']*["\'][^>]*>.*?<em[^>]*>(.*?)</em>',
            li_html, re.IGNORECASE | re.DOTALL
        )
        url_m = re.search(
            r'<a[^>]*href=["\']([^"\']+)["\']',
            li_html, re.IGNORECASE
        )
        if qual_m and url_m:
            name = name_m.group(1).strip() if name_m and name_m.group(1).strip() else "Direct Download"
            downloads.append({
                'name': name,
                'quality': qual_m.group(1).strip(),
                'url': url_m.group(1).strip()
            })

if downloads:
    print("[OK]  Found %d download link(s):\n" % len(downloads))
    for d in downloads:
        print(f"  [{d['quality']}] {d['name']}")
        print(f"        {d['url'][:80]}")
else:
    print("[FAIL]  No downloads found - check the HTML or the regex.")
    sys.exit(1)
