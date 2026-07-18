import sys
import urllib.parse
from playwright.sync_api import sync_playwright
import re as _re
from curl_cffi import requests

url = "https://go.akwam.com.co/link/143994"

print("Starting Playwright to get video URL...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    )
    page = context.new_page()

    video_url = None
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        html1 = page.content()
        dl_links = list(dict.fromkeys(_re.findall(r'href="(https?://[^"]+/download/[^"]+)"', html1)))
        
        if dl_links:
            download_page_url = dl_links[0]
            print("Goto download page:", download_page_url)
            page.goto(download_page_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for 5 seconds for JS to populate the URL
            page.wait_for_timeout(5000)
            html2 = page.content()
            
            # Find the actual mp4 link
            video_links = _re.findall(r'href="(https?://[^"]+\.mp4[^"]*)"', html2)
            if video_links:
                video_url = video_links[0]
                print("Found MP4 URL:", video_url)
            else:
                print("Could not find MP4 link in final page.")
                sys.exit(1)
        else:
            print("Could not find intermediate download page.")
            sys.exit(1)
            
    except Exception as e:
        print("Playwright Exception:", e)
        sys.exit(1)
    finally:
        browser.close()

if video_url:
    print("\nAttempting to stream with curl_cffi...")
    try:
        with requests.Session(impersonate="chrome120") as s:
            r = s.get(
                video_url,
                headers={
                    'Referer': download_page_url,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Connection': 'keep-alive'
                },
                stream=True
            )
            print("Proxy Response Status:", r.status_code)
            print("Proxy Headers:", r.headers)
            if r.status_code == 200:
                print("SUCCESS!")
            else:
                print("FAILED!")
    except Exception as e:
        print("curl_cffi Exception:", e)
