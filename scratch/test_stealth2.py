import sys
import time
from playwright.sync_api import sync_playwright

url = "https://go.akwam.com.co/link/143994"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    )
    page = context.new_page()

    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def handle_response(response):
        if (".mp4" in response.url or ".mkv" in response.url):
            print("<-", response.status, response.url)

    context.on("response", handle_response)

    try:
        print("Going to URL...")
        # Don't wait for domcontentloaded, just commit
        page.goto(url, wait_until='commit', timeout=60000)
        
        print("Waiting for network idle...")
        page.wait_for_load_state('networkidle', timeout=15000)
        
        print("Extracting download link...")
        dl_link = page.locator('a[href*="/download/"]').first.get_attribute('href')
        print("Download Link:", dl_link)
        
        print("Going to download page...")
        page.goto(dl_link, wait_until='commit')
        page.wait_for_load_state('networkidle', timeout=15000)
        
        print("Extracting MP4 link...")
        mp4_link = page.locator('a[href*=".mp4"]').first.get_attribute('href')
        print("MP4 Link:", mp4_link)
        
        print("Fetching MP4 directly using page.request.get...")
        r = page.request.get(mp4_link, headers={"Referer": dl_link})
        print("Response status:", r.status)
        
        if r.status == 200:
            print("SUCCESS! Playwright request context works!")
        else:
            print("FAILED! Even Playwright request context got 403!")
            
    except Exception as e:
        print("Exception:", str(e).encode('ascii', 'ignore').decode('ascii'), file=sys.stderr)
        
    browser.close()
