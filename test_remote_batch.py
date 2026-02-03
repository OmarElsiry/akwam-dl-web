import requests
import json
import re

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36',
    'Referer': 'https://ak.sv/'
}

# We'll test our local index.py logic by importing it or mimicking it
# Since index.py is a FastAPI app, we can test the class directly

# But for simplicity, let's just use the URL of the deployed app to see if it's working there after my push (if it redeployed)
# Or better, test the local version by running it if possible.
# Actually, the user asked to manually test the website https://akwam-dl-web-ul8s.vercel.app/
# So I should check if the FIX is live and working there.

def test_remote_batch(series_url):
    print(f"Testing remote batch for: {series_url}")
    api_url = f"https://akwam-dl-web-ul8s.vercel.app/api/akwam?action=batch&url={series_url}"
    try:
        resp = requests.get(api_url, timeout=60)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            results = resp.json()
            print(f"Resolved {len(results)} episodes")
            for r in results[:3]:
                print(f" - {r['title']}: {r['url'][:60]}... ({r['quality']})")
            
            # Check if links are direct (should not be ak.sv/download/...)
            if results and "/download/" in results[0]['url'] and "ak.sv" in results[0]['url']:
                print("\n❌ STILL NOT DIRECT! The link contains ak.sv")
            else:
                print("\n✅ Batch links look DIRECT (not pointing to ak.sv/download/)")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    bb_s1 = "https://ak.sv/series/67/breaking-bad-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84"
    test_remote_batch(bb_s1)
