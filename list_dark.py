from requests import get
import re

def list_dark():
    res_base = get('https://ak.sv/')
    base_url = res_base.url.rstrip('/')
    search_url = f"{base_url}/search?q=dark&section=series"
    print(f"Searching: {search_url}")
    res = get(search_url)
    pattern = rf'({base_url}/series/\d+/.*?)"'
    matches = re.findall(pattern, res.text)
    for m in matches:
        print(f"Match: {m}")

if __name__ == "__main__":
    list_dark()
