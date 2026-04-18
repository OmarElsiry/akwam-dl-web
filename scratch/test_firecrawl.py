from firecrawl import Firecrawl
import os
import json
import sys

# Set output encoding to UTF-8 for Arabic support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older python versions if needed
        pass

app = Firecrawl(api_key="fc-186b4e776b4042dfa4043a97c4985cc9")

def test_search():
    print("Searching for 'Avatar' on EgyDead...")
    # Search URL for EgyDead
    url = "https://egydead.live/?s=Avatar"
    
    # Using scrape to get content
    scrape_result = app.scrape(url, formats=['markdown'])
    
    print("Writing result to search_result.txt...")
    with open('search_result.txt', 'w', encoding='utf-8') as f:
        if hasattr(scrape_result, 'markdown'):
            f.write(scrape_result.markdown)
        else:
            f.write(str(scrape_result))
    
    print("Done. Check search_result.txt for the content.")

if __name__ == "__main__":
    test_search()
