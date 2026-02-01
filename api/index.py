from fastapi import FastAPI, Query, Request
import re
import requests
import json
from typing import Optional
from urllib.parse import quote, unquote

app = FastAPI()

@app.get("/")
async def root_status():
    return {
        "status": "online",
        "message": "Akwam-DL API is running!",
        "telegram_bot": "enabled",
        "web_ui": "ready"
    }

# --- CONSTANTS ---
RGX_DL_URL = r'https?://(\w*\.*\w+\.\w+/link/\d+)'
RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

BOT_TOKEN = "7917912042:AAHhtfKASDY54Q1U1X5650cWublsjtpvTi8"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- AKWAM LOGIC ---
class AkwamAPI:
    def __init__(self, base_url="https://ak.sv/"):
        self.base_url = base_url.rstrip('/')

    def search(self, query, _type='movie', page=1):
        search_url = f"{self.base_url}/search?q={query.replace(' ', '+')}&section={_type}&page={page}"
        resp = requests.get(search_url, headers=HEADERS)
        pattern = rf'({self.base_url}/{_type}/\d+/.*?)"'
        links = re.findall(pattern, resp.text)
        results = []
        for link in links:
            title = link.split('/')[-1].replace('-', ' ').title()
            results.append({
                'title': title,
                'url': link,
                'id': link.split('/')[-2]
            })
        return results

    def get_qualities(self, url):
        resp = requests.get(url, headers=HEADERS)
        page = resp.text.replace('\n', '')
        qualities = {}
        blocks = re.findall(r'<div class="tab-content quality.*?>(.*?)</div>', page)
        for block in blocks:
            q_match = re.search(r'>(\d+p)<', block)
            l_match = re.search(rf'href="({RGX_DL_URL})"', block)
            if q_match and l_match:
                qualities[q_match.group(1)] = l_match.group(1)
        return qualities

    def resolve_link(self, short_url):
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
        resp = requests.get(short_url, headers=HEADERS)
        shorten_match = re.search(RGX_SHORTEN_URL, resp.text)
        if not shorten_match:
            return None
        target_url = 'https://' + shorten_match.group(1)
        resp = requests.get(target_url, headers=HEADERS)
        if resp.url != target_url:
            resp = requests.get(resp.url, headers=HEADERS)
        direct_match = re.search(RGX_DIRECT_URL, resp.text)
        if direct_match:
            return 'https://' + direct_match.group(1)
        return None

# --- EGYDEAD LOGIC ---
class EgyDeadAPI:
    def __init__(self):
        self.base_url = "https://egydead.skin"

    def search(self, query):
        encoded_query = quote(query)
        url = f"{self.base_url}/?s={encoded_query}"
        resp = requests.get(url, headers=HEADERS)
        results = []
        movie_items = re.findall(r'<li class="movieItem">(.*?)</li>', resp.text, re.DOTALL)
        for item in movie_items:
            link_match = re.search(r'<a href="(.*?)"', item)
            title_match = re.search(r'<h1 class="BottomTitle">(.*?)</h1>', item)
            image_match = re.search(r'<img src="(.*?)"', item)
            if link_match and title_match:
                results.append({
                    'url': link_match.group(1),
                    'title': title_match.group(1),
                    'image': image_match.group(1) if image_match else None
                })
        return results

    def get_links(self, url):
        resp = requests.get(url, headers=HEADERS)
        links = []
        pattern1 = r'<span class="ser-name">(.*?)</span>.*?(?:<em>(.*?)</em>.*?)?href="(.*?)"'
        matches = re.findall(pattern1, resp.text, re.DOTALL)
        for match in matches:
            links.append({
                'server': match[0].strip(),
                'quality': match[1].strip() if match[1] else "Unknown",
                'url': match[2].strip()
            })
        if not links:
            items = re.findall(r'<a href="([^"]+)"[^>]*class="downloadv-item"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            for href, content in items:
                name_match = re.search(r'<div class="name">(.*?)</div>', content)
                server = name_match.group(1).strip() if name_match else "Unknown"
                quality = "Unknown"
                if "1080" in content: quality = "1080p"
                elif "720" in content: quality = "720p"
                elif "480" in content: quality = "480p"
                links.append({'server': server, 'quality': quality, 'url': href})
        
        episodes = []
        ep_links = re.findall(r'href="([^"]*/episode/[^"]+)"', resp.text)
        seen = set()
        for l in ep_links:
            if any(x in l.lower() for x in ['facebook', 'twitter', 'whatsapp', 'telegram', 'pinterest', 'reddit']):
                continue
            if l not in seen:
                seen.add(l)
                title = unquote(l.split('/')[-2]).replace('-', ' ').title()
                episodes.append({'url': l, 'title': title})
        return {"links": links, "episodes": episodes}

akwam_api = AkwamAPI()
egydead_api = EgyDeadAPI()

@app.get("/api/akwam")
async def handle_akwam(
    action: str, 
    q: Optional[str] = None, 
    type: Optional[str] = "movie", 
    url: Optional[str] = None
):
    if action == 'search':
        return akwam_api.search(q, type)
    elif action == 'details':
        return akwam_api.get_qualities(url)
    elif action == 'resolve':
        return {"direct_url": akwam_api.resolve_link(url)}
    return {"error": "Invalid action"}

@app.get("/api/egydead")
async def handle_egydead(
    action: str, 
    q: Optional[str] = None, 
    url: Optional[str] = None
):
    if action == 'search':
        return egydead_api.search(q)
    elif action == 'details':
        return egydead_api.get_links(url)
    return {"error": "Invalid action"}

# --- TELEGRAM BOT LOGIC ---

def send_telegram_msg(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.startswith("/start"):
            send_telegram_msg(chat_id, "<b>Welcome to Akwam-DL Bot!</b>\n\nSend me a query to search on Akwam, or use /egy [query] for EgyDead.")
        
        elif text.startswith("/egy"):
            query = text.replace("/egy", "").strip()
            if not query:
                send_telegram_msg(chat_id, "Please provide a search query. Example: /egy Batman")
                return
            results = egydead_api.search(query)
            if not results:
                send_telegram_msg(chat_id, "No results found on EgyDead.")
                return
            
            buttons = []
            for res in results[:8]:
                buttons.append([{"text": res["title"], "callback_data": f"egydetails|{res['url']}"}])
            
            send_telegram_msg(chat_id, f"<b>EgyDead Results for:</b> {query}", {"inline_keyboard": buttons})

        else:
            # Default to Akwam search
            query = text.strip()
            if not query: return
            results = akwam_api.search(query)
            if not results:
                send_telegram_msg(chat_id, "No results found on Akwam.")
                return
            
            buttons = []
            for res in results[:8]:
                buttons.append([{"text": res["title"], "callback_data": f"akdetails|{res['url']}"}])
            
            send_telegram_msg(chat_id, f"<b>Akwam Results for:</b> {query}", {"inline_keyboard": buttons})

    elif "callback_query" in data:
        cb = data["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        cb_data = cb["data"]

        if cb_data.startswith("akdetails|"):
            url = cb_data.split("|")[1]
            qualities = akwam_api.get_qualities(url)
            if not qualities:
                send_telegram_msg(chat_id, "No qualities found.")
                return
            
            buttons = []
            for q, l in qualities.items():
                buttons.append([{"text": q, "callback_data": f"akresolve|{l}|{q}"}])
            
            send_telegram_msg(chat_id, "<b>Choose Quality:</b>", {"inline_keyboard": buttons})

        elif cb_data.startswith("akresolve|"):
            _, short_url, quality = cb_data.split("|")
            send_telegram_msg(chat_id, f"🔄 Resolving {quality} link... please wait.")
            direct_url = akwam_api.resolve_link(short_url)
            if direct_url:
                send_telegram_msg(chat_id, f"✅ <b>Direct Link ({quality}):</b>\n\n<code>{direct_url}</code>\n\n<a href='{direct_url}'>🚀 FAST DOWNLOAD</a>")
            else:
                send_telegram_msg(chat_id, "❌ Failed to resolve link.")

        elif cb_data.startswith("egydetails|"):
            url = cb_data.split("|")[1]
            details = egydead_api.get_links(url)
            
            if details["episodes"]:
                buttons = []
                for ep in details["episodes"][:10]:
                    buttons.append([{"text": ep["title"], "callback_data": f"egydetails|{ep['url']}"}])
                send_telegram_msg(chat_id, "<b>Episodes:</b>", {"inline_keyboard": buttons})
            
            if details["links"]:
                text = "<b>Download Servers:</b>\n"
                for l in details["links"]:
                    text += f"• <a href='{l['url']}'>{l['server']}</a> ({l['quality']})\n"
                send_telegram_msg(chat_id, text)

    return {"status": "ok"}

@app.get("/api/set_webhook")
async def set_webhook(url: str):
    webhook_url = f"{url.rstrip('/')}/api/webhook"
    resp = requests.get(f"{TELEGRAM_API}/setWebhook", params={"url": webhook_url})
    return resp.json()
