import sys, re
sys.stdout.reconfigure(encoding='utf-8')

html = open('../scratch/debug_step4_b.html', encoding='utf-8').read()

# Find all inline script blocks
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S | re.I)
print(f'Found {len(scripts)} <script> blocks\n')
for i, s in enumerate(scripts):
    s = s.strip()
    if len(s) < 5:
        continue
    # Only print scripts that look relevant (contain URL-like strings or timer logic)
    if any(kw in s.lower() for kw in ['http', 'timer', 'count', 'redirect', 'location', 'src', 'url', 'file', 'link']):
        print(f'--- Script #{i} (len={len(s)}) ---')
        print(s[:2000])
        print()
