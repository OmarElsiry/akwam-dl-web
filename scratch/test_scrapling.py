import sys
import time
from scrapling import StealthyFetcher

url = "https://go.akwam.com.co/link/143994"

try:
    print("Starting StealthyFetcher...")
    fetcher = StealthyFetcher()
    
    print("Fetching URL:", url)
    page = fetcher.fetch(url, headless=True)
    
    dl_links = page.css('a[href*="/download/"]::attr(href)')
    if not dl_links:
        print("Failed to find download link")
        sys.exit(1)
        
    dl_url = dl_links[0]
    print("Going to download page:", dl_url)
    
    page2 = fetcher.fetch(dl_url, headless=True)
    
    # Wait for the JS to put the mp4 link in the page
    print("Waiting 5 seconds for JS execution...")
    time.sleep(5)
    
    # We might need to use Playwright's specific page object to evaluate if scrapling is just static HTML at this point.
    # StealthyFetcher returns a Selector, not a live page. Let's see if we can get the MP4 link.
    mp4_links = page2.css('a[href*=".mp4"]::attr(href)')
    if not mp4_links:
        print("No MP4 link found in static source. We need dynamic fetch.")
        # But wait, StealthyFetcher uses Camoufox/Playwright, doesn't it return the DOM after load?
        pass
    else:
        print("MP4 Link:", mp4_links[0])
        
except Exception as e:
    print("Exception:", e)
