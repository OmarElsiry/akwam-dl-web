import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        mp4_urls = []

        # Listen to all network requests
        page.on("request", lambda request: mp4_urls.append(request.url) if ".mp4" in request.url or ".m3u8" in request.url else None)

        print("Navigating to Episode 6 watch page...")
        await page.goto("https://akwam.com.co/episode/78411/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-6", wait_until="networkidle")

        print("Waiting a bit for any dynamic content...")
        await page.wait_for_timeout(3000)

        # Check if there's an iframe
        iframes = await page.query_selector_all("iframe")
        print(f"Found {len(iframes)} iframes.")
        for i, iframe in enumerate(iframes):
            src = await iframe.get_attribute("src")
            print(f"IFrame {i} src:", src)

        # Try to find a play button and click it
        play_btn = await page.query_selector(".play-btn, .vjs-big-play-button, button:has-text('Play')")
        if play_btn:
            print("Found play button, clicking it...")
            await play_btn.click()
            await page.wait_for_timeout(5000)
        else:
            print("No play button found. Dumping page content.")
            content = await page.content()
            with open("scratch/watch_page_dump.html", "w", encoding="utf-8") as f:
                f.write(content)

        print(f"Captured {len(mp4_urls)} media URLs:")
        for url in mp4_urls:
            print(url)

        await browser.close()

asyncio.run(main())
