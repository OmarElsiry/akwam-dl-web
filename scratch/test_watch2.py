from firecrawl import Firecrawl
app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")
url = "https://tv8.egydead.live/episode/the-boys-s05e03-1/"
try:
    result = app.scrape(url, formats=['html'])
    html = result.get('html', '') if isinstance(result, dict) else result.html
    print("Server in HTML?", "serversList" in html)
    print("watchNow in HTML?", 'class="watch' in html or 'id="watch' in html or 'watchNow' in html)
    print("iframe in HTML?", "iframe" in html)
    with open('watch2.html', 'w', encoding='utf-8') as f:
        f.write(html)
except Exception as e:
    print(f"Error: {e}")
