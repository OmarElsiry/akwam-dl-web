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
        if ".mp4" in response.url or ".mkv" in response.url:
            print("<-", response.status, response.url)

    context.on("response", handle_response)

    try:
        print("Going to URL...")
        page.goto(url, wait_until='commit', timeout=60000)
        
        # We need to wait for the page to load
        time.sleep(2)
        
        # Click the overlay to remove it
        print("Clicking overlay...")
        try:
            with context.expect_page(timeout=5000) as new_page_info:
                page.mouse.click(10, 10)
            ad_page = new_page_info.value
            ad_page.close()
            print("Ad closed.")
        except Exception as e:
            print("No ad popup:", str(e).encode('ascii', 'ignore').decode('ascii'))
            
        time.sleep(1)
        
        print("Extracting download link...")
        dl_link = page.locator('a[href*="/download/"]').first.get_attribute('href')
        print("Download Link:", dl_link)
        
        print("Going to download page...")
        page.goto(dl_link, wait_until='commit')
        time.sleep(2)
        
        # Click the second overlay
        print("Clicking second overlay...")
        try:
            with context.expect_page(timeout=5000) as new_page_info2:
                page.mouse.click(10, 10)
            ad_page2 = new_page_info2.value
            ad_page2.close()
            print("Second ad closed.")
        except Exception as e:
            print("No second ad popup:", str(e).encode('ascii', 'ignore').decode('ascii'))
            
        time.sleep(3) # Wait for countdown
        
        print("Extracting MP4 link...")
        mp4_link = page.locator('a[href*=".mp4"]').first.get_attribute('href')
        print("MP4 Link:", mp4_link)
        
        print("Fetching MP4 directly using page.request.get...")
        r = page.request.get(mp4_link, headers={"Referer": dl_link})
        print("Response status:", r.status)
        
    except Exception as e:
        print("Exception:", str(e).encode('ascii', 'ignore').decode('ascii'), file=sys.stderr)
        
    browser.close()
