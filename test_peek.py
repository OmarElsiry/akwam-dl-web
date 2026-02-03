import requests
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

def peek_qualities(url):
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    
    # Find positions of 'quality' and 'link/'
    idx = resp.text.find('quality')
    if idx != -1:
        print(f"--- Context around 'quality' ---")
        print(resp.text[idx-100:idx+300])
        
    idx2 = resp.text.find('link/')
    if idx2 != -1:
        print(f"\n--- Context around 'link/' ---")
        print(resp.text[idx2-100:idx2+300])

if __name__ == "__main__":
    peek_qualities("https://ak.sv/movie/6094/the-batman-1")
