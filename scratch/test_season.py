from firecrawl import Firecrawl
app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")
url = "https://tv8.egydead.live/season/%d9%85%d8%b3%d9%84%d8%b3%d9%84-the-boys-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-%d8%a7%d9%84%d8%b1%d8%a7%d8%a8%d8%b9-%d9%85%d8%aa%d8%b1%d8%ac%d9%85-%d9%83%d8%a7%d9%85%d9%84/"
result = app.scrape(url, formats=['markdown'])
with open('season_test.md', 'w', encoding='utf-8') as f:
    f.write(result.get('markdown', '') if isinstance(result, dict) else result.markdown)
