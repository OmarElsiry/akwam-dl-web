"""
Debug script to understand the direct URL extraction flow
"""
import re
from requests import get

HTTP = 'https://'
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'

# Test with a known quality link
quality_link = "go.ak.sv/link/8558"

print("="*60)
print("DEBUG: Direct URL Extraction Flow")
print("="*60)

print(f"\n1. Quality Link: {HTTP + quality_link}")

# Step 1: Get the shorten page
print("\n2. Fetching shorten page...")
page1 = get(HTTP + quality_link)
print(f"   Response URL: {page1.url}")
print(f"   Status: {page1.status_code}")

# Save for debug
with open('debug_page1.html', 'w', encoding='utf-8') as f:
    f.write(page1.content.decode())
print("   Saved to debug_page1.html")

# Try to find the shorten URL
shorten_matches = re.findall(RGX_SHORTEN_URL, page1.content.decode())
print(f"\n3. Shorten URL matches: {shorten_matches}")

if shorten_matches:
    shorten_url = HTTP + shorten_matches[0]
    print(f"\n4. Fetching shorten URL: {shorten_url}")
    page2 = get(shorten_url)
    print(f"   Response URL: {page2.url}")
    print(f"   Status: {page2.status_code}")
    
    # Save for debug
    with open('debug_page2.html', 'w', encoding='utf-8') as f:
        f.write(page2.content.decode())
    print("   Saved to debug_page2.html")
    
    # Check if redirected
    if shorten_url != page2.url:
        print(f"\n5. Redirected! Following...")
        page3 = get(page2.url)
        print(f"   Final URL: {page3.url}")
        
        with open('debug_page3.html', 'w', encoding='utf-8') as f:
            f.write(page3.content.decode())
        print("   Saved to debug_page3.html")
        
        direct_matches = re.findall(RGX_DIRECT_URL, page3.content.decode())
    else:
        direct_matches = re.findall(RGX_DIRECT_URL, page2.content.decode())
    
    print(f"\n6. Direct URL matches: {direct_matches}")
    
    if direct_matches:
        print(f"\n==> DIRECT DOWNLOAD URL: {HTTP + direct_matches[0]}")
    else:
        print("\n==> No direct URL found! Let's look for alternative patterns...")
        
        # Try more flexible patterns
        content = page2.content.decode() if not shorten_url != page2.url else page3.content.decode()
        
        # Pattern 1: Any download link
        alt_pattern1 = r'href="(https?://[^"]+/download/[^"]+)"'
        alt_matches1 = re.findall(alt_pattern1, content)
        print(f"   Alternative pattern 1 (href download): {alt_matches1[:3]}")
        
        # Pattern 2: JavaScript location
        alt_pattern2 = r'window\.location\.href\s*=\s*["\']([^"\']+)["\']'
        alt_matches2 = re.findall(alt_pattern2, content)
        print(f"   Alternative pattern 2 (js location): {alt_matches2[:3]}")
        
        # Pattern 3: data-url or similar
        alt_pattern3 = r'data-url=["\']([^"\']+)["\']'
        alt_matches3 = re.findall(alt_pattern3, content)
        print(f"   Alternative pattern 3 (data-url): {alt_matches3[:3]}")
else:
    print("\n==> No shorten URL found! Checking page structure...")
    
    # Look for any download patterns
    content = page1.content.decode()
    
    # All links with download
    all_download = re.findall(r'href="([^"]*download[^"]*)"', content, re.IGNORECASE)
    print(f"   All download hrefs: {all_download[:5]}")
    
    # All links with link
    all_link = re.findall(r'href="([^"]*link[^"]*)"', content, re.IGNORECASE)
    print(f"   All link hrefs: {all_link[:5]}")

print("\n" + "="*60)
print("DEBUG COMPLETE - Check debug_page*.html files for details")
print("="*60)
