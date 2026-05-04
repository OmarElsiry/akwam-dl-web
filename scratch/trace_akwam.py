import asyncio
from playwright.async_api import async_playwright

async def trace_network(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Navigating to {url}")
        
        # Intercept network requests
        requests_seen = []
        page.on("request", lambda request: requests_seen.append({"url": request.url, "method": request.method}))
        page.on("response", lambda response: print(f"Response: {response.status} {response.url}"))
        
        await page.goto(url, wait_until="domcontentloaded")
        
        print("Waiting for countdown (3 seconds)...")
        await asyncio.sleep(3)
        
        # Click the download button (a.download-link)
        btn = await page.query_selector('a.download-link')
        if btn:
            print("Found download button! Clicking...")
            # We use force=True to bypass ad overlays, but wait, if it opens a popup, let's catch it.
            try:
                await btn.click(force=True)
                await asyncio.sleep(2)
                await btn.click(force=True) # Double click just in case
                await asyncio.sleep(3)
            except Exception as e:
                print(f"Click error: {e}")
        else:
            print("No download button found on this page.")
            
        print("\n--- Network Trace ---")
        for req in requests_seen:
            if "mp4" in req["url"] or "download" in req["url"] or "api" in req["url"]:
                print(f"{req['method']} {req['url']}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(trace_network("https://akwam.com.co/download/177413/99188/%D8%A7%D9%84%D9%84%D8%B9%D8%A8%D8%A9-%D8%AC5-%D8%A7%D9%84%D9%83%D9%84%D8%A7%D8%B3%D9%8A%D9%83%D9%88/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-1"))
