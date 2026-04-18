import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('debug_search_batman.md', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'\*\*([^*]+)\*\*[^\]]*\]\((https?://[^)\s]+)\)'
for name, url in re.findall(pattern, text, re.DOTALL):
    name = name.strip()
    url = url.rstrip('/') + '/'
    print(f'{name} -> {url}')
    
    skip = False
    for part in SKIP_URL_PARTS:
        if part in url:
            skip = True
            break
            
    if name and url not in seen and not skip:
        seen.add(url)
        print(f'KEPT: {name} -> {url}')

