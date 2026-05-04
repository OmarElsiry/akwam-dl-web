import sys, re
sys.stdout.reconfigure(encoding='utf-8')

html = open('../scratch/debug_step4_b.html', encoding='utf-8').read()

# Find all <a> tags with href
all_a = re.findall(r'<a[^>]+>', html, re.I)
print(f'Total <a> tags: {len(all_a)}')
for a in all_a:
    if 'href' in a.lower() and not 'search' in a.lower() and not 'facebook' in a.lower() and not 'youtube' in a.lower():
        print(' ', a[:300])

print()
# Look for countdown timer div
timer_div = re.findall(r'(?i)(countdown|timer|count-down|btn-download)[^<>]*(?:<[^>]+>)*[^<>]*', html)
print('Timer-related elements:')
for t in timer_div[:10]:
    print(' ', repr(t[:200]))

print()
# Find the obfuscated script - it likely contains an encoded URL
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S | re.I)
big_script = max(scripts, key=len)
# Look for base64-like strings in the obfuscated eval script
b64_like = re.findall(r'[A-Za-z0-9+/]{40,}={0,2}', big_script)
print(f'Base64-like strings in big eval script ({len(b64_like)} found):')
for b in b64_like[:5]:
    print(' ', b[:100])
    try:
        import base64
        dec = base64.b64decode(b + '==').decode('utf-8', errors='ignore')
        if 'http' in dec or '.mp4' in dec or 'download' in dec:
            print('    [DECODED]:', dec[:200])
    except:
        pass
