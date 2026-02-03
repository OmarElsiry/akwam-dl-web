import re
try:
    with open('watch_page.html', 'r', encoding='utf-16') as f:
        data = f.read()
    
    # Search for any link containing /download/
    # Akwam often uses a button that looks like this:
    # <a href="https://ak.sv/download/..." class="download-link">
    
    links = re.findall(r'href="(https?://[^"]*?/download/[^"]+)"', data)
    print("Direct Download Links found:")
    for l in links:
        print(l)
    
    # Or maybe it's a redirect link
    redirects = re.findall(r'window\.location\.href\s*=\s*"(.*?)"', data)
    print("\nWindow Location Redirects:")
    for r in redirects:
        print(r)

except Exception as e:
    print(f"Error: {e}")
