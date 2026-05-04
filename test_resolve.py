import requests
r = requests.get('http://go.akwam.com.co/link/153885', allow_redirects=True)
with open('resolve_page.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
