import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import re

html = open('scratch/episode_page.html', 'r', encoding='utf-8').read()
no_nl = html.replace('\n', '')

RGX_QUALITY_TAG = r'data-quality="\d+".*?href="https?://([^"]+/link/\d+)"'
qualities_matches = re.findall(RGX_QUALITY_TAG, no_nl)

unique_links = []
for link in qualities_matches:
    if link not in unique_links:
        unique_links.append(link)
        
print('Matches:', unique_links)

q_labels = ['1080p', '720p', '480p', '360p', '240p']
i = 0
for q in q_labels:
    if f'>{q}</' in html and i < len(unique_links):
        print(f"Found quality {q} -> link {unique_links[i]}")
        i += 1
