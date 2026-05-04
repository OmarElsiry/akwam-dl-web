import asyncio
from playwright.async_api import async_playwright

async def get_mp4_via_browser(url: str) -> str:
    """
    Physically opens the Akwam download page in a headless browser,
    waits for the countdown, and forcefully clicks the download button
    to bypass ad overlays and capture the final .mp4 link.
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()

            mp4_url = None

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

            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for button
            try:
                await page.wait_for_selector('a.download, a:has-text("تحميل")', timeout=10000)
                btn = await page.query_selector('a.download, a:has-text("تحميل")')
                if btn:
                    # Double click to bypass transparent ad overlay
                    try:
                        await btn.click(force=True)
                        await page.wait_for_timeout(500)
                        await btn.click(force=True)
                    except Exception:
                        pass
                    
                    # Wait for capture
                    for _ in range(10):
                        if mp4_url:
                            break
                        await page.wait_for_timeout(500)
                        
                        href = await btn.get_attribute('href')
                        if href and '.mp4' in href:
                            mp4_url = href
                            break
            except Exception:
                pass

            await browser.close()
            return mp4_url
    except Exception as e:
        print(f"Browser extraction failed for {url}: {e}")
        return None
