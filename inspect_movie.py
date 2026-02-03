import re
try:
    with open('movie_page.html', 'r', encoding='utf-16') as f:
        data = f.read()
    # Find all links that look like quality links
    links = re.findall(r'href="(https?://[^"]*?(?:link|watch)/\d+)"', data)
    print("Found Links:")
    for l in links:
        print(l)
    
    # Try the specific pattern used in the code
    pattern = r'tab-content quality.*?a href="(https?://.*?(?:link|watch)/\d+)"'
    # Flatten it a bit for searching
    flat = data.replace('\n', ' ')
    specific = re.findall(pattern, flat)
    print("\nPattern Matches:")
    for s in specific:
        print(s)
except Exception as e:
    print(f"Error: {e}")
