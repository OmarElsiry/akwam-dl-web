from curl_cffi import requests

url = "https://tv8.egydead.live/?s=Avatar"
response = requests.get(url, impersonate="chrome110")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("Success! Title:", response.text.split('<title>')[1].split('</title>')[0])
else:
    print("Failed to bypass Cloudflare")
