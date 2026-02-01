from fastapi import FastAPI, Query, Request
import re
import requests
import json
from typing import Optional
from urllib.parse import quote, unquote

app = FastAPI()

# --- CONSTANTS (Synced with CLI v2.0) ---
RGX_DL_URL = r'https?://\w*\.*\w+\.\w+/link/\d+'
RGX_SHORTEN_URL = r'https?://\w*\.*\w+\.\w+/download/.*?"'
RGX_DIRECT_URL = r'[a-z0-9]{4,}\.\w+\.\w+/download/.*?"'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

BOT_TOKEN = "7917912042:AAHhtfKASDY54Q1U1X5650cWublsjtpvTi8"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

USER_STATES = {}

class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        try:
            resp = requests.get(base_url, headers=HEADERS, timeout=5)
            self.base_url = resp.url.rstrip('/')
        except:
            self.base_url = base_url.rstrip('/')

    def search(self, query, _type='movie', page=1):
        query = query.replace(' ', '+')
        search_url = f"{self.base_url}/search?q={query}&section={_type}&page={page}"
        resp = requests.get(search_url, headers=HEADERS)
        pattern = rf'({self.base_url}/{_type}/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
        results = []
        seen = set()
        for link in matches:
            if link not in seen:
                seen.add(link)
                title = link.split('/')[-1].replace('-', ' ').title()
                results.append({'title': title, 'url': link})
        return results

    def fetch_episodes(self, series_url):
        resp = requests.get(series_url, headers=HEADERS)
        # Support both absolute and relative episode links
        pattern = r'href="((?:https?://ak\.sv)?/episode/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
        episodes = []
        seen = set()
        for url in matches[::-1]:
            full_url = url if url.startswith('http') else f"{self.base_url}{url}"
            if full_url not in seen:
                seen.add(full_url)
                title = full_url.split('/')[-1].replace('-', ' ').title()
                # Extra clean for Arabic if needed
                title = unquote(title).replace('╪º┘ä╪\xad┘\x84┘\x82╪⌐', 'الحلقة')
                episodes.append({'title': title, 'url': full_url})
        return episodes

    def get_qualities(self, url):
        resp = requests.get(url, headers=HEADERS)
        page_content = resp.text.replace('\n', '')
        quality_pattern = rf'tab-content quality.*?a href="({RGX_DL_URL})"'
        parsed_links = re.findall(quality_pattern, page_content)
        qualities = {}
        i = 0
        for q in ['1080p', '720p', '480p']:
            if f'>{q}</' in resp.text and i < len(parsed_links):
                qualities[q] = parsed_links[i]
                i += 1
        return qualities

    def resolve_link(self, short_url):
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
        
        # Step 1: Shortened Link -> Download Page
        resp = requests.get(short_url, headers=HEADERS)
        match1 = re.search(f'({RGX_SHORTEN_URL})', resp.text)
        if not match1: return None
        
        target = match1.group(1).rstrip('"')
        if not target.startswith('http'): target = 'https://' + target
        
        # Step 2: Download Page -> Final Direct Link
        resp = requests.get(target, headers=HEADERS)
        if resp.url != target:
            resp = requests.get(resp.url, headers=HEADERS)
            
        match2 = re.search(f'({RGX_DIRECT_URL})', resp.text)
        if match2:
            final_url = match2.group(1).rstrip('"')
            return final_url if final_url.startswith('http') else 'https://' + final_url
        return None

akwam_api = AkwamAPI()

@app.get("/")
async def root_status():
    return {"status": "online", "message": "Akwam-DL API v2.0 Live"}

@app.get("/api/akwam")
async def handle_akwam(action: str, q: Optional[str] = None, type: Optional[str] = "movie", url: Optional[str] = None):
    if action == 'search': return akwam_api.search(q, type)
    if action == 'episodes': return akwam_api.fetch_episodes(url)
    if action == 'details': return akwam_api.get_qualities(url)
    if action == 'resolve': return {"direct_url": akwam_api.resolve_link(url)}
    return {"error": "Invalid action"}

# --- TELEGRAM BOT ---

def send_telegram(chat_id, text, markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if markup: payload["reply_markup"] = markup
    return requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

@app.post("/api/webhook")
async def webhook(request: Request):
    data = await request.json()
    if "message" in data:
        msg = data["message"]; cid = str(msg["chat"]["id"]); txt = msg.get("text", "")
        if txt.startswith("/start"):
            USER_STATES[cid] = 'movie'
            markup = {"inline_keyboard": [[{"text": "🎥 Movies", "callback_data": "m|movie"}, {"text": "📺 Series", "callback_data": "m|series"}]]}
            send_telegram(cid, "<b>Welcome to Akwam-DL!</b>\n\nChoose mode and send title:", markup)
        else:
            qtype = USER_STATES.get(cid, 'movie')
            res = akwam_api.search(txt, qtype)
            if not res: send_telegram(cid, "❌ No results.")
            else:
                btns = []
                for x in res[:10]:
                    # Extract ID to store in callback_data (to avoid 64-char limit)
                    # URL format: https://ak.sv/movie/123/slug
                    parts = x['url'].split('/')
                    # parts might be ['', 'movie', '123', 'slug'] or ['https:', '', 'ak.sv', 'movie', '123', 'slug']
                    obj_id = parts[-2] if parts[-1] else parts[-1] # Simple extraction
                    try:
                        obj_id = re.search(r'/(\d+)', x['url']).group(1)
                    except:
                        obj_id = parts[-2]

                    if qtype == 'series':
                        cb = f"ep|{obj_id}"
                    else:
                        cb = f"de|m|{obj_id}" # Details -> Movie -> ID
                    
                    btns.append([{"text": x['title'], "callback_data": cb}])
                send_telegram(cid, f"<b>Results ({qtype}):</b>", {"inline_keyboard": btns})
    elif "callback_query" in data:
        cb = data["callback_query"]; cid = str(cb["message"]["chat"]["id"]); d = cb["data"]
        if d.startswith("m|"):
            USER_STATES[cid] = d.split("|")[1]
            send_telegram(cid, f"✅ Mode: {USER_STATES[cid].title()}")
        
        elif d.startswith("ep|"):
            sid = d.split("|")[1]
            eps = akwam_api.fetch_episodes(f"{akwam_api.base_url}/series/{sid}")
            btns = []
            for e in eps[:15]:
                try: eid = re.search(r'/episode/(\d+)', e['url']).group(1)
                except: eid = e['url'].split('/')[-2]
                btns.append([{"text": e['title'], "callback_data": f"de|e|{eid}"}]) # Details -> Episode -> ID
            send_telegram(cid, "<b>Episodes:</b>", {"inline_keyboard": btns})
            
        elif d.startswith("de|"):
            # Format: de|type|id (de|m|123 or de|e|123)
            _, otype, oid = d.split("|")
            path = "movie" if otype == 'm' else "episode"
            qs = akwam_api.get_qualities(f"{akwam_api.base_url}/{path}/{oid}")
            btns = [[{"text": f"📥 {k}", "callback_data": f"res|{v}|{k}"}] for k, v in qs.items()]
            send_telegram(cid, "<b>Select Quality:</b>", {"inline_keyboard": btns})
            
        elif d.startswith("res|"):
            _, url, q = d.split("|")
            send_telegram(cid, f"⏳ Resolving {q}...")
            final = akwam_api.resolve_link(url)
            if final: send_telegram(cid, f"✅ <b>{q} Link:</b>\n\n<code>{final}</code>\n\n<a href='{final}'>🚀 DOWNLOAD</a>")
            else: send_telegram(cid, "❌ Resolution failed.")
    return {"ok": True}

@app.get("/api/set_webhook")
async def set_webhook(url: str):
    return requests.get(f"{TELEGRAM_API}/setWebhook", params={"url": f"{url}/api/webhook"}).json()
