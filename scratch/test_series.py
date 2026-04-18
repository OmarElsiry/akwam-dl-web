from firecrawl import Firecrawl
import json

app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")

try:
    search_res = app.scrape("https://tv8.egydead.live/?s=The+Boys", formats=['markdown'])
    print("Search returned ok")
    md = search_res.get('markdown', '') if isinstance(search_res, dict) else search_res.markdown
    with open('the_boys_search.md', 'w', encoding='utf-8') as f:
        f.write(md)
except Exception as e:
    print(e)
