import re
html = open('scratch/ep1_html.html', encoding='utf-8').read()
matches = re.findall(r'href=["\']([^"\']+\.mp4)["\']', html)
print(matches)
