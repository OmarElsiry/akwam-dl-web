import cloudscraper

scraper = cloudscraper.create_scraper()
url = "https://egydead.live/?s=Avatar"
response = scraper.get(url)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("Success! Title:", response.text.split('<title>')[1].split('</title>')[0])
else:
    print("Failed to bypass Cloudflare")
