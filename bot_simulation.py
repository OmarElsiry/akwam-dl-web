import re
import requests
import sys

# Set default encoding to utf-8 for stdout
sys.stdout.reconfigure(encoding='utf-8')

# --- CONSTANTS ---
RGX_DL_URL = r'https?://\w*\.*\w+\.\w+/link/\d+'
RGX_SHORTEN_URL = r'https?://\w*\.*\w+\.\w+/download/.*?"'
RGX_DIRECT_URL = r'[a-z0-9]{4,}\.\w+\.\w+/download/.*?"'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class AkwamCLIEmulator:
    def __init__(self, base_url="https://ak.sv/"):
        print("\n[BOT] Simulation Started: /start")
        resp = requests.get(base_url, headers=HEADERS, timeout=5)
        self.base_url = resp.url.rstrip('/')
        print(f"[BOT] Mode Selection Menu: [🎥 Movies] [📺 Series]")
        self.mode = None

    def set_mode(self, mode):
        self.mode = mode
        print(f"\n[USER] Clicks: {mode.title()} button")
        print(f"[BOT] Mode Set: {mode.title()}! Now send me a title.")

    def search(self, query):
        print(f"\n[USER] Sends text: \"{query}\"")
        url = f"{self.base_url}/search?q={query.replace(' ', '+')}&section={self.mode}"
        resp = requests.get(url, headers=HEADERS)
        pattern = rf'({self.base_url}/{self.mode}/\d+/.*?)"'
        matches = list(dict.fromkeys(re.findall(pattern, resp.text)))
        results = [{'title': m.split('/')[-1].replace('-', ' ').title(), 'url': m} for m in matches]
        
        print(f"[BOT] Results for \"{query}\":")
        for i, res in enumerate(results[:5]):
            print(f"  [{i+1}] {res['title']}")
        return results

    def fetch_episodes(self, series_url):
        print(f"\n[USER] Selects Series: {series_url.split('/')[-1]}")
        resp = requests.get(series_url, headers=HEADERS)
        pattern = rf'({self.base_url}/episode/\d+/.*?)"'
        matches = list(dict.fromkeys(re.findall(pattern, resp.text)))
        episodes = [{'title': m.split('/')[-1].replace('-', ' ').title(), 'url': m} for m in matches[::-1]]
        
        print(f"[BOT] Episodes for this series:")
        for i, ep in enumerate(episodes[:5]):
            print(f"  [{i+1}] {ep['title']}")
        return episodes

    def get_qualities(self, url):
        print(f"\n[USER] Selects Item/Episode: {url.split('/')[-1]}")
        resp = requests.get(url, headers=HEADERS)
        page = resp.text.replace('\n', '')
        pattern = rf'tab-content quality.*?a href="({RGX_DL_URL})"'
        links = re.findall(pattern, page)
        qualities = {}
        i = 0
        for q in ['1080p', '720p', '480p']:
            if f'>{q}</' in resp.text and i < len(links):
                qualities[q] = links[i]
                i += 1
        
        print(f"[BOT] Available Qualities:")
        for k in qualities.keys():
            print(f"  [📥 {k}]")
        return qualities

    def resolve(self, short_url, quality):
        print(f"\n[USER] Selects Quality: {quality}")
        print(f"[BOT] ⏳ Resolving {quality} link... please wait.")
        
        # Step 1: Initial Link
        resp = requests.get(short_url, headers=HEADERS)
        match = re.search(f'({RGX_SHORTEN_URL})', resp.text)
        if not match: 
            print("[BOT] ❌ Failed at Step 1")
            return None
        
        target = match.group(1).rstrip('"')
        if not target.startswith('http'): target = 'https://' + target
        
        # Step 2: Intermediate Page
        resp = requests.get(target, headers=HEADERS)
        if resp.url != target:
            resp = requests.get(resp.url, headers=HEADERS)
        
        # Step 3: Direct Link
        match = re.search(f'({RGX_DIRECT_URL})', resp.text)
        if match:
            url = match.group(1).rstrip('"')
            final_url = 'https://' + url
            print(f"[BOT] ✅ Direct Link Resolved!")
            print(f"[BOT] URL: {final_url}")
            return final_url
        
        print("[BOT] ❌ Failed at Step 3")
        return None

def run_simulation():
    bot = AkwamCLIEmulator()
    
    # --- MOVIE FLOW ---
    print("\n" + "="*40 + "\n--- SIMULATING MOVIE FLOW ---")
    bot.set_mode('movie')
    results = bot.search("Batman")
    if results:
        target = results[0]
        qs = bot.get_qualities(target['url'])
        if qs:
            first_q = list(qs.keys())[0]
            bot.resolve(qs[first_q], first_q)

    # --- SERIES FLOW ---
    print("\n" + "="*40 + "\n--- SIMULATING SERIES FLOW ---")
    bot.set_mode('series')
    results = bot.search("Suits")
    if results:
        target = results[0]
        eps = bot.fetch_episodes(target['url'])
        if eps:
            target_ep = eps[0]
            qs = bot.get_qualities(target_ep['url'])
            if qs:
                first_q = list(qs.keys())[0]
                bot.resolve(qs[first_q], first_q)

if __name__ == "__main__":
    run_simulation()
