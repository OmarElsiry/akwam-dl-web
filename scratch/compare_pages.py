"""
Analyze the screenshot of a failed episode to understand what the page shows.
Also look at the actual page HTML that was captured in the Playwright sessions.
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

# Check the failing episode pages using requests to see what HTML we get
# compared to what the working episodes returned.
# The key difference: the download JS sets href only after a session token check.

import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
    'Referer': 'https://go.akwam.com.co/link/143997',
}

# Test ep 6 (fails) vs ep 7 (works) - look for structural differences
for ep, url in [
    ("Ep6 (FAIL)", "https://akwam.com.co/download/143997/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6"),
    ("Ep7 (WORKS)", "https://akwam.com.co/download/143998/78412/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-7"),
]:
    print(f"\n=== {ep} ===")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        html = r.text
        
        # Look for the key JS that sets the download href
        # Find the countdown/download-related script
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
        for s in scripts:
            if 'download' in s.lower() and ('href' in s.lower() or 'attr' in s.lower() or 'setTimeout' in s):
                print(f"Relevant script block (len={len(s)}):")
                print(s[:800])
                print()
        
        # Look for the file-name or countdown element
        countdown = re.findall(r'(?i)(count|timer|seconds|ثواني)[^<>]*(?:<[^>]+>)*[^<>]*', html)
        print(f"Countdown refs: {countdown[:3]}")
        
        # Look for any data encoding in the page
        encoded_blocks = re.findall(r'(?:atob|btoa|base64|encodeURI)\s*\(["\']([^"\']{30,})["\']', html)
        print(f"Encoded blocks: {encoded_blocks[:3]}")
        
        # Check if both pages have same structure
        has_file_name = 'file-name' in html
        has_countdown = 'countdown' in html.lower() or 'count' in html.lower()
        print(f"has file-name class: {has_file_name}")
        print(f"has countdown: {has_countdown}")
        print(f"HTML length: {len(html)}")
        
    except Exception as e:
        print(f"Error: {e}")
