import requests
import re
import json

# Pre-compiled regex
RE_SHORTEN = re.compile(r'href="(https?://[^"]+?/download/[^"]+)"')
RE_DIRECT = re.compile(r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"')
RE_LINK = re.compile(r'href="(https?://[^"]+?/link/\d+)"')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

def get_qualities(url):
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = 'utf-8'
    all_links = RE_LINK.findall(resp.text)
    possible_labels = ['1080p', '720p', '480p', '360p', 'Full HD', 'HD', 'SD']
    label_pattern = '|'.join(possible_labels)
    found_labels = re.findall(rf'>\s*({label_pattern})\s*<', resp.text)
    qualities = {}
    for i, link in enumerate(all_links):
        label = found_labels[i] if i < len(found_labels) else f"Quality {i+1}"
        qualities[label] = link
    return qualities

def resolve_link(short_url):
    if not short_url.startswith('http'):
        short_url = 'https://' + short_url
    resp = requests.get(short_url, headers=HEADERS)
    match1 = RE_SHORTEN.search(resp.text)
    if match1:
        target = match1.group(1)
    elif "/download/" in resp.url:
        target = resp.url
    else:
        return None
    target = target.rstrip('"')
    if not target.startswith('http'): target = 'https://' + target
    resp = requests.get(target, headers=HEADERS)
    if resp.url != target:
        resp = requests.get(resp.url, headers=HEADERS)
    match2 = RE_DIRECT.search(resp.text)
    if match2:
        final_url = match2.group(1).rstrip('"')
        return final_url if final_url.startswith('http') else 'https://' + final_url
    return None

print("=== TESTING BREAKING BAD EPISODE ===")
ep_url = "https://ak.sv/episode/781/granite-state"
quals = get_qualities(ep_url)
print(f"Qualities found: {list(quals.keys())}")
if quals:
    target_q = list(quals.keys())[0]
    print(f"Resolving: {target_q}")
    direct = resolve_link(quals[target_q])
    print(f"FINAL DIRECT URL: {direct}")
