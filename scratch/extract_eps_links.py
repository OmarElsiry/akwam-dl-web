import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scratch/episode_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("Server links:")
# Find server list, typically under a ul or div with class 'servers' or similar
# Let's just find any links that look like a watch server link
servers = re.findall(r'<a[^>]+href=["\'](https://akwam.com.co/watch/[^"\']+)["\'][^>]*>.*?</a>', html, re.S)
for s in servers:
    print(s)

print("\nQuality download links:")
dl = re.findall(r'<a[^>]+href=["\'](https://go\.akwam\.com\.co/link/\d+)["\'][^>]*>.*?<span[^>]*>(.*?)</span>', html, re.S)
for l, q in dl:
    print(f"{q.strip()} -> {l}")
