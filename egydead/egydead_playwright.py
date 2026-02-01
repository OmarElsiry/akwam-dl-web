import sys
import time
import re
from playwright.sync_api import sync_playwright

def get_final_link(page, url):
    try:
        print(f"Navigating to {url}...")
        page.goto(url, timeout=60000)
        
        if "dood" in url or "dsvplay" in url:
            return resolve_doodstream(page)
        elif "1fichier" in url:
            return resolve_1fichier(page)
        elif "hglink" in url:
            return resolve_hglink(page)
        
        return url
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def resolve_doodstream(page):
    print("Resolving DoodStream...")
    try:
        # 1. Click 'Download Now'
        download_btn = page.locator("a.btn.btn-primary.download_vd:has-text('Download Now')")
        if download_btn.count() > 0:
            print("Found 'Download Now' button. Clicking...")
            download_btn.click(force=True)
            
            # Wait for 'High quality' link to appear (it might be on the same page or after reload)
            print("Waiting for 'High quality' link...")
            try:
                page.wait_for_selector("a:has-text('High quality')", timeout=10000)
            except:
                print("Timed out waiting for 'High quality'.")

        # 2. Click 'High quality' (this usually navigates to the final download page)
        high_quality_link = page.locator("a:has-text('High quality')")
        if high_quality_link.count() > 0:
            print("Found 'High quality' link. Clicking to navigate...")
            high_quality_link.click()
            page.wait_for_load_state('networkidle')
            
        # 3. Click 'Download file' (this triggers the actual download)
        download_file_link = page.locator("a:has-text('Download file')")
        if download_file_link.count() > 0:
            href = download_file_link.get_attribute("href")
            print(f"Found 'Download file' link: {href}")
            
            print("Triggering download...")
            try:
                with page.expect_download(timeout=15000) as download_info:
                    download_file_link.click()
                download = download_info.value
                print(f"Download started: {download.suggested_filename}")
                # download.save_as(download.suggested_filename)
                return href
            except Exception as e:
                print(f"Download trigger failed: {e}")
                return href
        
        # Fallback: Check if we are already on a page with a direct video source
        video = page.locator("video")
        if video.count() > 0:
            src = video.get_attribute("src")
            print(f"Found video src: {src}")
            return src

    except Exception as e:
        print(f"DoodStream resolution failed: {e}")
    
    return page.url

def resolve_1fichier(page):
    print("Resolving 1fichier...")
    # 1fichier usually requires clicking a button to show the link or start download
    # For now, just return the current URL as it's often the download page itself
    return page.url

def resolve_hglink(page):
    print("Resolving Hglink...")
    # Hglink is a redirector. Just wait for it to settle.
    page.wait_for_load_state('networkidle')
    print(f"Redirected to: {page.url}")
    return page.url

def resolve_url(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        final_link = get_final_link(page, url)
        
        browser.close()
        return final_link

def main():
    if len(sys.argv) < 2:
        print("Usage: python egydead_playwright.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    final_link = resolve_url(url)
    print(f"\nFINAL LINK: {final_link}")

if __name__ == "__main__":
    main()
