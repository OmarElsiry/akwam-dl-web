import re
text = open('direct2.html', encoding='utf-8').read()
m = re.search(r'https?://([^"]+)"\s+download', text)
if m:
    print(m.group(1))
else:
    print("No match")
