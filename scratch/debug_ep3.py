import requests, re

# Follow the main download page for EP3
url = 'https://akwam.com.co/download/143994/78408/bloodhounds-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84/%D8%A7%D9%84%D8%AD%D9%84%D9%82%D8%A9-3'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}
r = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
print('Status:', r.status_code)
print('Final URL:', r.url[:150])
print('Content-Type:', r.headers.get('content-type', 'none'))

html = r.text

# Look for direct file links
mp4s = re.findall(r'https?://[^"\'\s]+\.mp4', html)
print('\nMP4 links found:', mp4s[:5])

# Look for downet URLs
downet = re.findall(r'https?://[^"\'\s]*downet[^"\'\s]*', html)
print('Downet URLs:', downet[:5])

# Look for any JS variable with download URL
js_urls = re.findall(r'(?:var|let|const)\s+\w+\s*=\s*["\']([^"\'\s]+(?:download|mp4|mkv)[^"\'\s]*)', html)
print('JS var URLs:', js_urls[:5])

# Look for token patterns
tokens = re.findall(r'(token|direct_link|file_url|download_url)\s*[:=]\s*["\']([^"\']+)', html)
print('Tokens:', tokens[:5])

# Look for onclick or data-* attributes with URLs
data_urls = re.findall(r'(?:data-url|onclick|href)\s*=\s*["\']([^"\']*(?:download|mp4)[^"\']*)', html)
print('Data URLs:', data_urls[:5])

# Save full HTML for inspection
with open('scratch/ep3_download_page.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('\nSaved HTML to scratch/ep3_download_page.html')
print('HTML length:', len(html))
