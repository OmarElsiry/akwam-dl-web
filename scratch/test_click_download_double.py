import asyncio
from playwright.async_api import async_playwright

async def get_final_mp4(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()

        mp4_url = None

        # Hook to capture popup or requests
        def handle_request(req):
            nonlocal mp4_url
            if ".mp4" in req.url and "thumb" not in req.url:
                mp4_url = req.url
        page.on("request", handle_request)

        async def handle_popup(popup):
            nonlocal mp4_url
            if ".mp4" in popup.url:
                mp4_url = popup.url

        page.on("popup", handle_popup)

        try:
            print(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded")
            
            print("Waiting for countdown and download button...")
            # Wait for the button to be visible
            await page.wait_for_selector('a.download, a:has-text("تحميل")', timeout=15000)
            btn = await page.query_selector('a.download, a:has-text("تحميل")')
            
            if btn:
                print("Clicking download button (first time - might be ad overlay)...")
                try:
                    await btn.click(force=True)
                except Exception as e:
                    print("First click exception:", e)
                
                await page.wait_for_timeout(1000)
                
                if not mp4_url:
                    print("Clicking download button (second time - real download)...")
                    try:
                        await btn.click(force=True)
                    except Exception as e:
                        print("Second click exception:", e)
                
                print("Waiting to capture URL...")
                for _ in range(15):
                    if mp4_url:
                        break
                    await page.wait_for_timeout(1000)
                    
                    # check if the href attribute updated
                    href = await btn.get_attribute('href')
                    if href and '.mp4' in href:
                        mp4_url = href
                        break
            else:
                print("Download button not found")
        except Exception as e:
            print("Error waiting for button:", e)

        print(f"Final mp4_url: {mp4_url}")
        await browser.close()
        return mp4_url

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    url7 = "https://akwam.com.co/download/143998/78412/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-7"
    print("\nTesting Ep 7...")
    asyncio.run(get_final_mp4(url7))
