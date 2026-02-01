import sys
import requests
import re
from egydead_dl import EgyDeadDL

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

def main():
    dl = EgyDeadDL()
    # URL for The Day of the Jackal Ep 1 (from previous debug)
    # https://egydead.skin/episode/%d9%85%d8%b3%d9%84%d8%b3%d9%84-the-day-of-the-jackal-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-1-%d9%85%d8%aa%d8%b1%d8%ac%d9%85%d8%a9/
    # Encoded: https://egydead.skin/episode/%d9%85%d8%b3%d9%84%d8%b3%d9%84-the-day-of-the-jackal-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-1-%d9%85%d8%aa%d8%b1%d8%ac%d9%85%d8%a9/
    # I'll use the unencoded version if possible or just fetch the series page and find it again to be safe
    
    print("Searching for The Day of the Jackal...")
    results = dl.search("The Day of the Jackal")
    target = results[0] # Assuming first is correct based on previous run
    
    print(f"Target Series: {target['title']}")
    resp = requests.get(target['url'], headers=dl.headers)
    
    episode_links = re.findall(r'href="([^"]*/episode/[^"]+)"', resp.text)
    episode_links = [link for link in list(set(episode_links)) if not link.endswith("/episode/")]
    
    # Sort and pick Ep 1 (last in list usually if sorted by name, but let's just pick one)
    ep1_url = None
    for link in episode_links:
        if "1-" in link or "10-" in link: # Just picking one
            ep1_url = link
            break
    
    if not ep1_url:
        ep1_url = episode_links[0]

    print(f"Checking Episode URL: {ep1_url}")
    
    # Get links using the class method
    links = dl.get_download_links(ep1_url)
    print(f"Found {len(links)} download links:")
    for l in links:
        print(f" - {l['server']}: {l['url']}")

if __name__ == "__main__":
    main()
