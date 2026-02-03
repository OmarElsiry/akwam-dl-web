import re
try:
    with open('watch_page.html', 'r', encoding='utf-16') as f:
        data = f.read()
    
    # Look for the download button link
    # Pattern: r'https?://.*?/download/.*?"'
    links = re.findall(r'https?://[^"]*?/download/[^"]*', data)
    print("Download Links found:")
    for l in links:
        print(l)
    
    # Check for script-based redirection as well
    scripts = re.findall(r'window\.location\s*=\s*"(.*?)"', data)
    print("\nScript Redirects:")
    for s in scripts:
        print(s)

except Exception as e:
    print(f"Error: {e}")
