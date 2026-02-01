from fastapi import FastAPI, Query, Request
import re
import requests
import json
from typing import Optional
from urllib.parse import quote, unquote

app = FastAPI()

# --- CONSTANTS ---
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

BOT_TOKEN = "7917912042:AAHhtfKASDY54Q1U1X5650cWublsjtpvTi8"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# In-memory session state
USER_STATES = {}

# --- AKWAM LOGIC (IMPROVED FROM CLI) ---
class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        # Resolve initial redirect if any
        try:
            resp = requests.get(base_url, headers=HEADERS, timeout=5)
            self.base_url = resp.url.rstrip('/')
        except:
            self.base_url = base_url.rstrip('/')

    def search(self, query, _type='movie', page=1):
        query = query.replace(' ', '+')
        search_url = f"{self.base_url}/search?q={query}&section={_type}&page={page}"
        resp = requests.get(search_url, headers=HEADERS)
        
        # Regex from CLI logic
        pattern = rf'({self.base_url}/{_type}/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
        
        results = []
        # CLI uses [::-1] to reverse, but usually, we want the most relevant first.
        # However, to match the "algorithm" exactly, I'll follow the CLI patterns.
        seen = set()
        for link in matches:
            if link not in seen:
                seen.add(link)
                title = link.split('/')[-1].replace('-', ' ').title()
                results.append({
                    'title': title,
                    'url': link,
                    'id': link.split('/')[-2]
                })
        return results

    def fetch_episodes(self, series_url):
        resp = requests.get(series_url, headers=HEADERS)
        pattern = rf'({self.base_url}/episode/\d+/.*?)"'
        matches = re.findall(pattern, resp.text)
        
        episodes = []
        seen = set()
        # The CLI reverses the matches [::-1]
        for url in matches[::-1]:
            if url not in seen:
                seen.add(url)
                title = url.split('/')[-1].replace('-', ' ').title()
                episodes.append({
                    'title': title,
                    'url': url
                })
        return episodes

    def get_qualities(self, url):
        resp = requests.get(url, headers=HEADERS)
        page_content = resp.text.replace('\n', '')
        
        # Regex from CLI logic
        # RGX_QUALITY_TAG = rf'tab-content quality.*?a href="{RGX_DL_URL}"'
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
        
        # Phase 1: Shortened URL
        resp = requests.get(short_url, headers=HEADERS)
        shorten_match = re.search(RGX_SHORTEN_URL, resp.text)
        if not shorten_match:
            return None
        
        target_url = 'https://' + shorten_match.group(1)
        
        # Phase 2: Getting Direct URL page
        resp = requests.get(target_url, headers=HEADERS)
        
        # Handle non-direct URL fix from CLI
        if resp.url != target_url:
            resp = requests.get(resp.url, headers=HEADERS)
            
        # Phase 3: Extract Final URL
        direct_match = re.search(RGX_DIRECT_URL, resp.text)
        if direct_match:
            return 'https://' + direct_match.group(1)
        return None

akwam_api = AkwamAPI()

@app.get("/")
async def root_status():
    return {
        "status": "online",
        "message": "Akwam-DL API (CLI-Logic v2.0) is running!",
        "telegram_bot": "enabled"
    }

@app.get("/api/akwam")
async def handle_akwam(
    action: str, 
    q: Optional[str] = None, 
    type: Optional[str] = "movie", 
    url: Optional[str] = None
):
    if action == 'search':
        return akwam_api.search(q, type)
    elif action == 'episodes':
        return akwam_api.fetch_episodes(url)
    elif action == 'details':
        return akwam_api.get_qualities(url)
    elif action == 'resolve':
        return {"direct_url": akwam_api.resolve_link(url)}
    return {"error": "Invalid action"}

# --- TELEGRAM BOT LOGIC ---

def send_telegram_msg(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" in data:
        message = data["message"]
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")

        if text.startswith("/start"):
            USER_STATES[chat_id] = 'movie'
            welcome_text = (
                "<b>🎬 Akwam-DL Bot (CLI v2.0 Logic)</b>\n\n"
                "I am now using the improved search and link resolution algorithm.\n\n"
                "<i>Current Mode: Movies</i>\n"
                "Choose your mode and then send me a title to search."
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "🎥 Movies", "callback_data": "menu|movie"}, {"text": "📺 Series", "callback_data": "menu|series"}]
                ]
            }
            send_telegram_msg(chat_id, welcome_text, markup)
        
        else:
            q_type = USER_STATES.get(chat_id, 'movie')
            query = text.strip()
            if not query: return
            
            results = akwam_api.search(query, q_type)
            if not results:
                send_telegram_msg(chat_id, f"❌ No results found for <b>{query}</b>.")
                return
            
            buttons = []
            for res in results[:10]:
                callback_prefix = "akepisodes|" if q_type == 'series' else "akdetails|"
                buttons.append([{"text": res["title"], "callback_data": f"{callback_prefix}{res['url']}"}])
            
            send_telegram_msg(chat_id, f"<b>Results for:</b> {query}\n(Mode: {q_type.title()})", {"inline_keyboard": buttons})

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = str(cb["message"]["chat"]["id"])
        cb_data = cb["data"]

        if cb_data.startswith("menu|"):
            q_type = cb_data.split("|")[1]
            USER_STATES[chat_id] = q_type
            send_telegram_msg(chat_id, f"✅ <b>Mode Set: {q_type.title()}</b>\n\nSend me the title you want to search for.")

        elif cb_data.startswith("akepisodes|"):
            url = cb_data.split("|")[1]
            episodes = akwam_api.fetch_episodes(url)
            if not episodes:
                send_telegram_msg(chat_id, "❌ No episodes found for this series.")
                return
            
            buttons = []
            # Only show first 15 episodes to stay within Telegram limits
            for ep in episodes[:15]:
                buttons.append([{"text": ep["title"], "callback_data": f"akdetails|{ep['url']}"}])
            
            send_telegram_msg(chat_id, "<b>Select Episode:</b>", {"inline_keyboard": buttons})

        elif cb_data.startswith("akdetails|"):
            url = cb_data.split("|")[1]
            qualities = akwam_api.get_qualities(url)
            if not qualities:
                send_telegram_msg(chat_id, "❌ No download links found.")
                return
            
            buttons = []
            for q, l in qualities.items():
                buttons.append([{"text": f"📥 {q}", "callback_data": f"akresolve|{l}|{q}"}])
            send_telegram_msg(chat_id, "<b>Select Quality:</b>", {"inline_keyboard": buttons})

        elif cb_data.startswith("akresolve|"):
            _, short_url, quality = cb_data.split("|")
            send_telegram_msg(chat_id, f"⏳ Resolving <b>{quality}</b> link...")
            direct_url = akwam_api.resolve_link(short_url)
            if direct_url:
                send_telegram_msg(chat_id, f"✅ <b>Link Resolved ({quality}):</b>\n\n<code>{direct_url}</code>\n\n<a href='{direct_url}'>🚀 DOWNLOAD NOW</a>")
            else:
                send_telegram_msg(chat_id, "❌ Failed to resolve link. The download page might be down.")

    return {"status": "ok"}

@app.get("/api/set_webhook")
async def set_webhook(url: str):
    webhook_url = f"{url.rstrip('/')}/api/webhook"
    resp = requests.get(f"{TELEGRAM_API}/setWebhook", params={"url": webhook_url})
    return resp.json()
