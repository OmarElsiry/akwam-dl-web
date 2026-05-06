import requests

# Test the akwam-stream endpoint directly
url = 'http://127.0.0.1:8000/api/akwam-stream?link_id=go.akwam.com.co/link/143994'
print(f'Testing: {url}')

headers = {
    'Range': 'bytes=0-1024',
}

try:
    r = requests.get(url, headers=headers, stream=True, timeout=60)
    print(f'Status: {r.status_code}')
    print(f'Content-Type: {r.headers.get("content-type")}')
    print(f'Content-Length: {r.headers.get("content-length")}')
    print(f'Content-Range: {r.headers.get("content-range")}')
    print(f'Accept-Ranges: {r.headers.get("accept-ranges")}')
    
    # Read first chunk
    chunk = next(r.iter_content(chunk_size=1024), None)
    if chunk:
        print(f'First chunk size: {len(chunk)} bytes')
        print(f'First 20 bytes (hex): {chunk[:20].hex()}')
    else:
        print('No data received!')
        print(f'Response text: {r.text[:500]}')
    r.close()
except Exception as e:
    print(f'Error: {e}')
