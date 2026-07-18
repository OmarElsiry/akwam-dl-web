import sys, re
sys.stdout.reconfigure(encoding='utf-8')

html = open('../scratch/debug_step4_b.html', encoding='utf-8').read()

cdn_links = re.findall(r'(https?://[a-z0-9._-]+\.[a-z]{2,}/[^\s"\'<>]+)', html)
print('CDN-like links (first 20):')
for l in cdn_links[:20]:
    print(' ', l)

print()
js_urls = re.findall(r"window\.location[^'\"]*['\"]([^'\"]+)['\"]", html)
print('window.location URLs:', js_urls[:10])

print()
meta_refresh = re.findall(r'content=["\'][^"\']*url=([^\s"\'>;]+)', html, re.I)
print('Meta refresh:', meta_refresh[:5])

print()
forms = re.findall(r'action=["\'](https?://[^"\']+)["\']', html, re.I)
print('Form actions:', forms[:5])

print()
data_attrs = re.findall(r'data-[a-z-]*=["\']([^"\']{15,})["\']', html)
print('data-* attrs with URLs (first 10):', data_attrs[:10])

print()
idx = html.lower().find('download')
if idx != -1:
    print('Snippet around first "download":')
    print(repr(html[max(0,idx-200):idx+500]))
