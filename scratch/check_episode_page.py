"""
Check the episode page directly for stream URLs (iframe, player source, etc.)
The /watch/ or /episode/ page may have a video player with a direct stream link.
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '..')
from api.akwam_api import safe_get

episode_url = 'https://akwam.com.co/episode/78413/bloodhounds-الموسم-الاول/الحلقة-8'
print(f'Fetching episode page: {episode_url}')

r = safe_get(episode_url)
print(f'Status: {r.status_code}  Final URL: {r.url}')
html = r.text

# Save for inspection
open('../scratch/episode_page.html', 'w', encoding='utf-8').write(html)
print(f'Saved (len={len(html)})')

print()
# Look for iframe embeds
iframes = re.findall(r'<iframe[^>]*src=["\']([^"\']+)["\'][^>]*>', html, re.I)
print('Iframes:')
for f in iframes:
    print(' ', f)

print()
# Look for video source
video_srcs = re.findall(r'<source[^>]*src=["\']([^"\']+)["\']', html, re.I)
print('Video sources:', video_srcs)

print()
# Look for player/embed scripts
player_vars = re.findall(r'(?:file|src|source|stream|url)\s*[:=]\s*["\']([^"\']{20,})["\']', html, re.I)
print('Player vars (first 15):')
for v in player_vars[:15]:
    print(' ', v)

print()
# Look for any m3u8 or mp4 URL
video_urls = re.findall(r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)', html)
print('Direct video URLs:', video_urls)

print()
# Look for iframe with embed or player
embed_iframes = re.findall(r'<iframe[^>]*>.*?</iframe>', html, re.I | re.S)
print(f'Iframe blocks: {len(embed_iframes)}')
for f in embed_iframes[:3]:
    print(' ', f[:300])
