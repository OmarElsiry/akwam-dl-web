from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import re
import requests
import json
import os
from typing import Optional
from urllib.parse import quote, unquote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONSTANTS (Directly from v2.0 CLI) ---
RGX_DL_URL = r'https?://\w*\.*\w+\.\w+/link/\d+'
RGX_SHORTEN_URL = r'https?://\w*\.*\w+\.\w+/download/.*?"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
RGX_QUALITY_TAG = r'tab-content quality.*?a href="(https?://\w*\.*\w+\.\w+/link/\d+)"'

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
            resp.encoding = 'utf-8'
            self.base_url = resp.url.rstrip('/')
        except:
            self.base_url = base_url.rstrip('/')

    def search(self, query, _type='movie', page=1):
        query = query.replace(' ', '+')
        url = f"{self.base_url}/search?q={query}&section={_type}&page={page}"
        resp = requests.get(url, headers=HEADERS)
        resp.encoding = 'utf-8'
        
        clean_base = self.base_url.rstrip('/')
        pattern = rf'({clean_base}/{_type}/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
        
        results = []
        seen = set()
        for link in matches[::-1]:
            if link not in seen:
                seen.add(link)
                slug = link.split('/')[-1]
                title = unquote(slug).replace('-', ' ').title()
                # Ensure the URL is absolute
                full_url = link if link.startswith('http') else f"{clean_base}{link}"
                results.append({'title': title, 'url': full_url})
        return results

    def fetch_episodes(self, series_url):
        resp = requests.get(series_url, headers=HEADERS)
        resp.encoding = 'utf-8'
        clean_base = self.base_url.rstrip('/')
        
        # Broad pattern to catch absolute and relative links
        # Looking for href="/episode/..." or href="https://ak.sv/episode/..."
        pattern = r'href="((?:https?://ak\.sv)?/episode/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
            
        episodes = []
        seen = set()
        for link in matches[::-1]:
            # Construct full absolute URL
            full_url = link if link.startswith('http') else f"{clean_base}{link}"
            if full_url not in seen:
                seen.add(full_url)
                slug = full_url.split('/')[-1]
                title = unquote(slug).replace('-', ' ').title()
                episodes.append({'title': title, 'url': full_url})
        return episodes

    def get_qualities(self, url):
        resp = requests.get(url, headers=HEADERS)
        resp.encoding = 'utf-8'
        page_content = resp.text.replace('\n', '')
        
        # Search for link/... identifiers inside quality blocks
        parsed_links = re.findall(RGX_QUALITY_TAG, page_content)
        
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

    def batch_resolve(self, series_id):
        # Mirroring CLI's recursive_episodes
        series_url = f"{self.base_url}/series/{series_id}"
        episodes = self.fetch_episodes(series_url)
        results = []
        
        # Limit to 15 episodes to prevent Vercel timeout (10s limit)
        for ep in episodes[:15]:
            qualities = self.get_qualities(ep['url'])
            if qualities:
                # Pick first available quality (usually highest)
                q_key = list(qualities.keys())[0]
                direct = self.resolve_link(qualities[q_key])
                if direct:
                    results.append({"title": ep['title'], "url": direct})
        return results

akwam_api = AkwamAPI()

@app.get("/")
async def root_ui():
    # Robust path resolution for Vercel
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_path = os.path.join(base_dir, "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "UI file (index.html) not found", "path_searched": index_path}

@app.get("/style.css")
async def style_css():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return FileResponse(os.path.join(base_dir, "style.css"), media_type="text/css")

@app.get("/script.js")
async def script_js():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return FileResponse(os.path.join(base_dir, "script.js"), media_type="application/javascript")

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
                for x in res:
                    # Compact ID extraction to keep callback < 64 bytes
                    try:
                        obj_id = re.search(r'/(\d+)', x['url']).group(1)
                        if qtype == 'series':
                            cb = f"ep|{obj_id}"
                        else:
                            cb = f"de|m|{obj_id}"
                        btns.append([{"text": x['title'], "callback_data": cb}])
                    except: continue
                send_telegram(cid, f"<b>Results ({qtype}):</b>", {"inline_keyboard": btns[:10]})
    
    elif "callback_query" in data:
        cb = data["callback_query"]; cid = str(cb["message"]["chat"]["id"]); d = cb["data"]
        
        # Mode Selection
        if d.startswith("m|"):
            USER_STATES[cid] = d.split("|")[1]
            send_telegram(cid, f"✅ Mode: {USER_STATES[cid].title()}\nNow send me the title you want to search for.")
        
        # Fetch Episodes for Series ID
        elif d.startswith("ep|"):
            sid = d.split("|")[1]
            eps = akwam_api.fetch_episodes(f"{akwam_api.base_url}/series/{sid}")
            if not eps:
                send_telegram(cid, "❌ No episodes found or page layout changed.")
                return {"ok": True}
            
            btns = []
            for e in eps[:14]: # Show first 14
                try:
                    eid = re.search(r'/episode/(\d+)', e['url']).group(1)
                    btns.append([{"text": e['title'], "callback_data": f"de|e|{eid}"}])
                except: continue
            
            # THE "GET ALL" OPTION
            btns.append([{"text": "🔥 GET ALL EPISODES 🔥", "callback_data": f"all|{sid}"}])
            
            send_telegram(cid, "<b>Episodes Found:</b>", {"inline_keyboard": btns})
            
        elif d.startswith("all|"):
            sid = d.split("|")[1]
            send_telegram(cid, "⏳ Resolving all episodes (First 15)... This may take a few seconds.")
            all_links = akwam_api.batch_resolve(sid)
            
            if not all_links:
                send_telegram(cid, "❌ Failed to resolve episodes. Try one by one.")
            else:
                text = "📁 <b>Season Download Links:</b>\n\n"
                for l in all_links:
                    text += f"• <b>{l['title']}:</b>\n<code>{l['url']}</code>\n\n"
                
                # If text too long for one msg, it might need splitting, but for 15 it should fit
                send_telegram(cid, text)

        # Details (Qualities) for Movie or Episode ID
        elif d.startswith("de|"):
            _, otype, oid = d.split("|")
            path = "movie" if otype == 'm' else "episode"
            full_url = f"{akwam_api.base_url}/{path}/{oid}"
            qs = akwam_api.get_qualities(full_url)
            if not qs:
                send_telegram(cid, "❌ No qualities found for this item.")
                return {"ok": True}
                
            btns = [[{"text": f"📥 {k}", "callback_data": f"res|{v}|{k}"}] for k, v in qs.items()]
            send_telegram(cid, "<b>Select Quality:</b>", {"inline_keyboard": btns})
            
        # Resolve Final Link
        elif d.startswith("res|"):
            _, url, q = d.split("|")
            # Telegram might escape characters in callback, ensure URL is clean
            send_telegram(cid, f"⏳ Resolving <b>{q}</b>... please wait.")
            final = akwam_api.resolve_link(url)
            if final:
                send_telegram(cid, f"✅ <b>{q} Link:</b>\n\n<code>{final}</code>\n\n<a href='{final}'>🚀 DOWNLOAD</a>")
            else:
                send_telegram(cid, "❌ Resolution failed. Akwam might be protecting this link or site is down.")
                
    return {"ok": True}

@app.get("/api/set_webhook")
async def set_webhook(url: str):
    return requests.get(f"{TELEGRAM_API}/setWebhook", params={"url": f"{url}/api/webhook"}).json()
