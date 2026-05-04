import sys, re, requests
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def extract_with_session(ep_num, ep_url, link_id, dl_page):
    session = requests.Session()
    session.headers.update(HEADERS)
    
    print(f"\n--- Episode {ep_num} ---")
    
    # 1. Visit Episode Page
    try:
        print(f"Visiting episode page: {ep_url}")
        r1 = session.get(ep_url, timeout=10)
    except Exception as e:
        print(f"Failed ep page: {e}")
        
    # 2. Visit Link Page
    link_url = f"https://go.akwam.com.co/link/{link_id}"
    try:
        print(f"Visiting link page: {link_url}")
        session.headers.update({'Referer': ep_url})
        r2 = session.get(link_url, timeout=10)
    except Exception as e:
        print(f"Failed link page: {e}")
        
    # 3. Visit Download Page
    try:
        print(f"Visiting dl page: {dl_page}")
        session.headers.update({'Referer': link_url})
        r3 = session.get(dl_page, timeout=10)
        
        # Check for URL in HTML
        RGX_DOWNLOAD_HREF = re.compile(
            r"""\$\s*\(\s*['"]a\.download['"]\s*\)\s*\.attr\s*\(\s*['"]href['"]\s*,\s*['"]([^'"]+)['"]\s*\)""",
            re.IGNORECASE
        )
        m = RGX_DOWNLOAD_HREF.search(r3.text)
        if m:
            print(f"  [OK] Found direct link: {m.group(1)}")
        else:
            print(f"  [NO MATCH] No link found in HTML.")
            # Check if there is an error message
            if "not found" in r3.text.lower() or "404" in r3.text:
                print("  [ERROR] Page shows not found / 404.")
    except Exception as e:
        print(f"Failed dl page: {e}")

extract_with_session(6, 
    "https://akwam.com.co/episode/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6",
    143997,
    "https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6")
    
extract_with_session(8, 
    "https://akwam.com.co/episode/78413/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-8",
    143999,
    "https://akwam.com.co/download/143999/78413/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-8")

