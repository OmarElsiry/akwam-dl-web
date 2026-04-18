import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('debug_search_batman.md', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'\[(.*?)\]\((https?://[^ )\s\"]+)\)'
for raw_name, url in re.findall(pattern, text):
    # Clean up raw_name
    name = re.sub(r'!\[.*?\]\(.*?\)', '', raw_name) # remove images
    name = re.sub(r'[*_]', '', name) # remove bold/italic
    name = name.strip()
    if name:
        print(f'{name} -> {url}')
