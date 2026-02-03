import requests
import re
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

def get_qualities(url):
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    
    all_links = re.findall(r'href="(https?://[^"]+?/link/\d+)"', resp.text)
    
    possible_labels = ['1080p', '720p', '480p', '360p', 'Full HD', 'HD', 'SD']
    label_pattern = '|'.join(possible_labels)
    # Using non-greedy to avoid capturing too much if spacers exist
    found_labels = re.findall(f'>\s*({label_pattern})\s*<', resp.text)
    
    print(f"Links found: {len(all_links)}")
    print(f"Labels found: {len(found_labels)}")
    
    qualities = {}
    for i, link in enumerate(all_links):
        label = found_labels[i] if i < len(found_labels) else f"Quality {i+1}"
        qualities[label] = link
            
    return qualities

if __name__ == "__main__":
    url = "https://ak.sv/movie/6094/the-batman-1"
    res = get_qualities(url)
    print(json.dumps(res, indent=4))
