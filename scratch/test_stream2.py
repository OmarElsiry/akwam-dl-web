import sys, re
sys.path.insert(0, '.')
from api.akwam_api import AkwamAPI

ak = AkwamAPI()

link_id = 'go.akwam.com.co/link/143994'

print("=== Testing stream_video (same session) ===")
resp, info = ak.stream_video(link_id)
if resp is None:
    print("stream_video returned None!")
else:
    print(f"Status: {info['status_code']}")
    print(f"CT: {info['content_type']}")
    print(f"CL: {info['content_length']}")
    print(f"CR: {info['content_range']}")
    if info['status_code'] == 403:
        print(f"Response body: {resp.text[:500]}")
    else:
        chunk = next(resp.iter_content(1024), None)
        if chunk:
            print(f"First chunk: {len(chunk)} bytes, hex: {chunk[:16].hex()}")
    resp.close()

print("\n=== Testing get_fresh_stream_url + manual fetch ===")
session, mp4_url, dl_page = ak.get_fresh_stream_url(link_id)
if mp4_url:
    print(f"MP4 URL: {mp4_url}")
    print(f"DL Page: {dl_page}")
    print(f"Session cookies: {dict(session.cookies)}")
    
    # Try with the same session
    print("\n--- Attempt 1: Same session, Referer=dl_page ---")
    r = session.get(mp4_url, headers={'Referer': dl_page}, stream=True, timeout=15)
    print(f"  Status: {r.status_code}, CT: {r.headers.get('content-type')}")
    if r.status_code == 200:
        chunk = next(r.iter_content(1024), None)
        print(f"  Chunk: {len(chunk)} bytes") if chunk else print("  No data")
    else:
        print(f"  Body: {r.text[:300]}")
    r.close()

    # Try with the same session but Referer=mp4_url 
    print("\n--- Attempt 2: Same session, Referer=mp4_url ---")
    r = session.get(mp4_url, headers={'Referer': mp4_url}, stream=True, timeout=15)
    print(f"  Status: {r.status_code}, CT: {r.headers.get('content-type')}")
    if r.status_code == 200:
        chunk = next(r.iter_content(1024), None)
        print(f"  Chunk: {len(chunk)} bytes") if chunk else print("  No data")
    r.close()
    
    # Try with same session, no extra headers
    print("\n--- Attempt 3: Same session, no extra headers ---")
    r = session.get(mp4_url, stream=True, timeout=15)
    print(f"  Status: {r.status_code}, CT: {r.headers.get('content-type')}")
    if r.status_code == 200:
        chunk = next(r.iter_content(1024), None)
        print(f"  Chunk: {len(chunk)} bytes") if chunk else print("  No data")
    r.close()
    
    # Check what the CDN returns - maybe it redirects?
    print("\n--- Attempt 4: Same session, allow_redirects=False ---")
    r = session.get(mp4_url, stream=True, timeout=15, allow_redirects=False)
    print(f"  Status: {r.status_code}")
    print(f"  Location: {r.headers.get('location')}")
    r.close()
    
    # Try HEAD to see what we get
    print("\n--- Attempt 5: HEAD request ---")
    r = session.head(mp4_url, timeout=15, allow_redirects=True)
    print(f"  Status: {r.status_code}, CT: {r.headers.get('content-type')}, CL: {r.headers.get('content-length')}")
    r.close()
else:
    print("get_fresh_stream_url returned None!")
