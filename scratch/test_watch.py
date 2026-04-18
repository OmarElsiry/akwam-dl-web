from firecrawl import Firecrawl
app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")
url = "https://egydead.live/episode/%d9%85%d8%b3%d9%84%d8%b3%d9%84-attack-on-titan-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-%d8%a7%d9%84%d8%a7%d9%88%d9%84-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-1-%d8%a7%d9%84%d8%a7%d9%88%d9%84%d9%8a/"
try:
    result = app.scrape(url, formats=['html'])
    html = result.get('html', '') if isinstance(result, dict) else result.html
    print("Server in HTML?", "serversList" in html)
    print("watchNow in HTML?", "watchNow" in html)
    with open('watch.html', 'w', encoding='utf-8') as f:
        f.write(html)
except Exception as e:
    print(f"Error: {e}")
