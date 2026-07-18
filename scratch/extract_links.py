import re
content = open('scratch/ep1_html.html', encoding='utf-8').read()
links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', content)
with open('scratch/ep1_links.txt', 'w', encoding='utf-8') as f:
    for l in links:
        f.write(l + '\n')
