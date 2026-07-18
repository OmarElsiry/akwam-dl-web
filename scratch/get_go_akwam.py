import requests, sys
sys.stdout.reconfigure(encoding='utf-8')
html = requests.get('https://go.akwam.com.co/link/143997', headers={'User-Agent': 'Mozilla/5.0'}).text
with open('scratch/go_akwam_ep6.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Dumped go.akwam.com.co to scratch/go_akwam_ep6.html")
