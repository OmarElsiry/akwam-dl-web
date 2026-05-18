"""Debug: analyze the saved episode HTML to understand quality/link structure."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import re

html = open('scratch/episode_page.html', 'r', encoding='utf-8').read()
no_nl = html.replace('\n', '')

# Find all data-quality attributes and their associated links
print('=== data-quality + link patterns ===')
matches = re.findall(r'data-quality="(\d+)".*?/link/(\d+)', no_nl)
print(f'Found {len(matches)} matches:')
for q, link_id in matches:
    print(f'  quality={q}, link_id={link_id}')

# Find where quality labels appear
print()
print('=== Where quality labels appear ===')
for q_label in ['1080p', '720p', '480p', '360p']:
    idx = html.find(f'>{q_label}</')
    if idx >= 0:
        context = html[max(0,idx-200):idx+50]
        print(f'  {q_label} found at offset {idx}')

# Check the tab buttons
print()
print('=== Tab buttons ===')
tab_buttons = re.findall(r'tab-btn.*?data-tab="(.*?)".*?>(.*?)<', no_nl)
for tab_id, label in tab_buttons:
    print(f'  tab={tab_id}, label={label.strip()}')

# All tab-content IDs
print()
print('=== All tab-content IDs ===')
tab_contents = re.findall(r'tab-content.*?id="(tab-\d+)"', no_nl)
for tc in tab_contents:
    print(f'  {tc}')

# Quality divs with server+quality
print()
print('=== Quality divs with server+quality ===')
q_divs = re.findall(r'data-server="(\d+)"\s*data-quality="(\d+)"', html)
for server, quality in q_divs:
    print(f'  server={server}, quality={quality}')

# Try a broader approach: find all hrefs with /link/ and nearby quality info
print()
print('=== All /link/ hrefs with context ===')
for m in re.finditer(r'href="(https?://[^"]*?/link/\d+)"', html):
    start = max(0, m.start() - 300)
    context = html[start:m.start()]
    # Extract data-quality from context
    dq = re.findall(r'data-quality="(\d+)"', context)
    print(f'  URL: {m.group(1)}')
    if dq:
        print(f'  data-quality: {dq[-1]}')

# Check what the old regex expected vs new structure
print()
print('=== Testing old regex ===')
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_QUALITY_TAG = rf'tab-content quality.*?a href="{RGX_DL_URL}"'
old_matches = re.findall(RGX_QUALITY_TAG, no_nl)
print(f'Old RGX_QUALITY_TAG: {len(old_matches)} matches')

# Try adapted regex
NEW_RGX = r'data-quality="(\d+)".*?href="(https?://[^"]*?/link/\d+)"'
new_matches = re.findall(NEW_RGX, no_nl)
print()
print('=== New approach: data-quality + link ===')
print(f'Found {len(new_matches)} matches:')
for quality_id, url in new_matches:
    print(f'  quality_id={quality_id}, url={url}')

# Check the quality ID mapping
print()
print('=== Looking for quality ID to label mapping ===')
# Search for patterns like "720" near quality identifiers
for pat in re.finditer(r'quality.*?(\d{3,4})p', no_nl):
    print(f'  {pat.group()[:100]}')
