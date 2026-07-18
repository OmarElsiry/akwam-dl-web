import re
with open('scratch/go_akwam_ep6.html', encoding='utf-8') as f:
    html = f.read()

links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html)
for link in links:
    if 'download' in link or 'two.akw' in link or 'akw-cdn' in link:
        print(link)
