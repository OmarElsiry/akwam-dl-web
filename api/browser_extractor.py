import re
import time
from typing import Optional, Tuple
from urllib.parse import urlparse, urljoin

# Partner/referrer sites that unlock "video embed restricted" anti-bot walls
# on EarnVids-style embed hosts. The player only loads when the page is opened
# with one of these as the Referer.
PARTNER_REFERERS = [
    'https://tv10.egydead.live/',
    'https://wecima.cx/',
    'https://sahid4u.com/',
    'https://faselhd.com/',
    'https://egydead.skin/',
    'https://mycima.cx/',
    'https://ak.sv/',
    'https://faselhd.rip/',
    'https://wecima.show/',
    'https://vidspeed.org/',
    'https://callistanise.com/',
    'https://playmogo.com/',
]

# Hosts that are genuinely dead / impossible to automate (no browser attempt).
BLOCKED_EMBED_HOSTS = []


def _host_is_blocked(url: str) -> bool:
    """Quick check if the embed host is known to be impossible to automate."""
    host = urlparse(url).netloc.lower()
    for blocked in BLOCKED_EMBED_HOSTS:
        if blocked in host:
            return True
    return False


def _embed_host(url: str) -> str:
    """Return scheme://netloc for a URL (used as the manifest Referer)."""
    p = urlparse(url)
    return f'{p.scheme}://{p.netloc}'


# Init script injected before page scripts: patch XHR/fetch so we can record
# every URL the player requests (including HLS manifests that don't end in
# .m3u8, e.g. "...urlset/master.txt"), AND capture the response body of any
# manifest response (the player's own request is the only reliable way to get
# the bytes — the CDN serves it via a Service Worker / hls.js, so it never
# shows up as a normal Playwright response event).
_CAPTURE_INIT = """
(() => {
  const isMan = (u) => /urlset|master\\.txt|\\.m3u8|\\.m3u|manifest|playlist/i.test(String(u || ''));
  const L = (u) => { try { window.__cap = window.__cap || []; window.__cap.push(String(u)); } catch(e){} };
  const store = (u, body) => { try { if (body && /#EXTM3U/.test(body)) { window.__man = window.__man || {}; window.__man[String(u)] = body; } } catch(e){} };
  const _o = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m, u, ...a){ this.__u = u; return _o.call(this, m, u, ...a); };
  const _s = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function(...a){
    if (this.__u) L(this.__u);
    if (this.__u && isMan(this.__u)) {
      this.addEventListener('load', () => { try { store(this.__u, this.responseText); } catch(e){} });
    }
    return _s.call(this, ...a);
  };
  const _f = window.fetch;
  window.fetch = function(u, ...a){
    const s = (u && u.url) || String(u); L(s);
    const p = _f.call(this, u, ...a);
    if (s && isMan(s)) {
      p.then(r => r.clone().text().then(t => store(s, t)).catch(()=>{})).catch(()=>{});
    }
    return p;
  };
})();
"""


def _is_manifest_url(u: str) -> bool:
    """Heuristic: does this URL look like an HLS master/playlist?"""
    if not u or u.startswith('blob:'):
        return False
    low = u.lower()
    return (
        '.m3u8' in low
        or 'master.txt' in low
        or 'urlset' in low
        or '/playlist' in low
        or low.endswith('.m3u')
        or 'manifest' in low
    )


# Full-file video extensions (exclude HLS segments like .ts/.woff2).
_VIDEO_FILE_EXTS = ('.mp4', '.mkv', '.webm', '.m4v', '.mov')
_AD_DOMAINS = (
    'doubleclick', 'googlesyndication', 'google-analytics',
    'exoclick', 'popads', 'adsterra', 'propellerads',
)


def _first_video_file(captured) -> Optional[str]:
    """From a set of requested URLs, return the most likely direct video
    file URL (mp4/webm/mkv/...), ignoring ad domains."""
    cands = []
    for u in captured:
        lu = (u or '').lower()
        if any(lu.endswith(e) for e in _VIDEO_FILE_EXTS) and not any(
            d in lu for d in _AD_DOMAINS
        ):
            cands.append(u)
    if not cands:
        return None
    # Prefer the longest URL (real video paths tend to be longer than ads).
    cands.sort(key=len, reverse=True)
    return cands[0]


def capture_hls_manifest(embed_url: str, referer: str = None, cookies: list = None,
                         timeout_ms: int = 20000) -> Optional[str]:
    """
    Open an embed video page in a headless Chromium browser, unlock the
    anti-bot player wall, and capture the HLS manifest URL (master playlist)
    that the player fetches.

    Returns the manifest URL (verified fetchable with Referer = embed host),
    or None if nothing was found.
    """
    if _host_is_blocked(embed_url):
        print(f"[BrowserResolver] Skipping blocked host: {embed_url[:60]}")
        return None

    from playwright.sync_api import sync_playwright

    embed_origin = _embed_host(embed_url)
    candidates = []
    if referer:
        candidates.append(referer)
    candidates += PARTNER_REFERERS
    # de-dupe, preserve order
    seen = set()
    candidates = [c for c in candidates if not (c in seen or seen.add(c))]

    # Hosts that check document.referrer via JS and need navigation from a real page
    REFERRER_CHECK_HOSTS = ['callistanise.com', 'fastvid.cam', 'fastved.cam']

    embed_hostname = urlparse(embed_url).netloc.lower()
    needs_real_referrer = any(d in embed_hostname for d in REFERRER_CHECK_HOSTS)

    last_err = None
    for cand in candidates:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--autoplay-policy=no-user-gesture-required'],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 720},
                    extra_http_headers={
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Referer": cand,
                    },
                )

                # Replay the end-user's real session cookies (forwarded from the
                # partner site) so gated players (Mixdrop / vinovo / shaaheid4u)
                # actually load their source in this headless context.
                if cookies:
                    try:
                        from urllib.parse import urlparse as _up2
                        _host = _up2(embed_url).netloc
                        _norm = []
                        for _c in cookies:
                            if not isinstance(_c, dict) or not _c.get('name'):
                                continue
                            _nc = {
                                'name': _c['name'],
                                'value': str(_c.get('value', '')),
                                'path': _c.get('path') or '/',
                            }
                            _dom = (_c.get('domain') or _c.get('host') or _host)
                            _nc['domain'] = _dom.lstrip('.')
                            if _c.get('secure') is not None:
                                _nc['secure'] = bool(_c['secure'])
                            _norm.append(_nc)
                        if _norm:
                            context.add_cookies(_norm)
                    except Exception as _e:
                        print(f"[BrowserResolver] add_cookies failed: {_e}")

                page = context.new_page()
                captured = set()
                manifest_bodies = {}

                BLOCKED_DOMAINS = [
                    'doubleclick.net', 'googlesyndication.com', 'google-analytics.com',
                    'googletagmanager.com', 'facebook.net', 'scorecardresearch.com',
                    'quantserve.com', 'exoclick.com', 'popads.net', 'adsterra.com',
                    'propellerads.com', 'adservice.google.com',
                ]
                BLOCKED_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
                                '.woff', '.woff2', '.ttf', '.eot']

                def handle_route(route):
                    url = route.request.url
                    if any(d in url for d in BLOCKED_DOMAINS):
                        route.abort()
                        return
                    if any(url.endswith(ext) for ext in BLOCKED_EXTS):
                        route.abort()
                        return
                    # Intercept the HLS manifest so we can read its body
                    # reliably (the player fetches it as arraybuffer via a
                    # Service Worker, so it's never a normal response event).
                    if _is_manifest_url(url):
                        try:
                            resp = route.fetch()
                            body = resp.body()
                            if body and b'#EXTM3U' in body:
                                manifest_bodies[url] = body.decode('utf-8', 'replace')
                            route.fulfill(resp)
                            return
                        except Exception:
                            pass
                    route.continue_()

                page.route("**/*", handle_route)
                page.add_init_script(_CAPTURE_INIT)

                def on_request(req):
                    captured.add(req.url)

                page.on("request", on_request)

                # For hosts that check document.referrer via JS, navigate from
                # the partner page so the browser sets document.referrer correctly.
                if needs_real_referrer:
                    try:
                        page.goto(cand, wait_until="domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    try:
                        page.evaluate(f"window.location = '{embed_url}'")
                        page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                    except Exception as e:
                        last_err = e
                else:
                    try:
                        page.goto(embed_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    except Exception as e:
                        last_err = e

                # Quick check for "embed restricted" — skip this referer immediately
                try:
                    body_text = page.evaluate("() => document.body.innerText")
                    if body_text and 'embed restricted' in body_text.lower():
                        browser.close()
                        continue
                except Exception:
                    pass

                # Nudge the player: some embeds (Mixdrop, VideoJS, shaaheid4u
                # SPA) only start loading their source after a real click/play.
                # For mixdrop-style hosts, click the center overlay first
                try:
                    page.wait_for_timeout(500)
                    # Try clicking the play button overlay using the "Play Video" text
                    try:
                        play_btn = page.query_selector('text=Play Video')
                        if play_btn:
                            play_btn.click()
                            page.wait_for_timeout(1000)
                    except Exception:
                        pass
                    page.mouse.click(640, 360)
                except Exception:
                    pass

                # Poll for the manifest URL
                deadline = time.time() + min(28, max(10, timeout_ms / 700))
                manifest = None
                while time.time() < deadline:
                    manifest = next((u for u in captured if _is_manifest_url(u)), None)
                    if manifest and manifest in manifest_bodies:
                        body = manifest_bodies[manifest]
                        if body and '#EXTM3U' in body:
                            browser.close()
                            return manifest, body

                    # Check jwplayer config for a file URL
                    try:
                        js = page.evaluate(
                            "() => { try { var i = jwplayer(); if (i && i.getConfig) {"
                            " var it = i.getConfig().playlist; if (it && it[0] && it[0].file) return it[0].file; }"
                            " } catch(e){} return null; }"
                        )
                        if js and _is_manifest_url(js):
                            captured.add(js)
                            manifest = js
                    except Exception:
                        pass

                    # Check Video.js players for their current source
                    try:
                        js = page.evaluate(
                            "() => { try {"
                            " var pls = window.videojs && window.videojs.players;"
                            " if (!pls) return null;"
                            " var ks = Object.keys(pls);"
                            " for (var i = 0; i < ks.length; i++) {"
                            "   var p = pls[ks[i]];"
                            "   if (!p) continue;"
                            "   var s = p.currentSrc && p.currentSrc();"
                            "   if (!s) s = p.src && (typeof p.src === 'function' ? p.src() : p.src);"
                            "   if (s && typeof s === 'string') return s;"
                            "   if (s && s.src) return s.src;"
                            " }"
                            " } catch(e){} return null; }"
                        )
                        if js and (_is_manifest_url(js)
                                   or '.mp4' in js.lower() or '.m3u8' in js.lower()):
                            captured.add(js)
                            manifest = js
                    except Exception:
                        pass

                    # Force playback so preload="none" / play-gated players
                    # (Mixdrop, VideoJS, etc.) actually request their source.
                    try:
                        page.evaluate(
                            "() => { try {"
                            " document.querySelectorAll('video').forEach(function(v){"
                            "   try { v.muted = true; v.play(); } catch(e){} });"
                            " var vs = window.videojs && window.videojs.players"
                            "   ? Object.values(window.videojs.players) : [];"
                            " vs.forEach(function(pl){ try { pl.play && pl.play(); } catch(e){} });"
                            " if (window.player && window.player.play) { try { window.player.play(); } catch(e){} }"
                            " } catch(e){} }"
                        )
                    except Exception:
                        pass

                    # Capture the player's resolved source if set directly.
                    try:
                        cs = page.evaluate(
                            "() => { try {"
                            " var v = document.querySelector('video');"
                            " if (!v) return null;"
                            " var src = v.currentSrc || v.src || '';"
                            " if (src && src.startsWith('blob:')) {"
                            "   try { src = v.getAttribute('src') || ''; } catch(e){}"
                            " }"
                            " if (!src) {"
                            "   src = v.getAttribute('data-src') || v.getAttribute('data-base') || '';"
                            " }"
                            " return src || null;"
                            " } catch(e){ return null; } }"
                        )
                        if cs and ('.mp4' in cs.lower() or '.m3u8' in cs.lower()
                                   or '.webm' in cs.lower() or '.mkv' in cs.lower()
                                   or any(d in cs.lower() for d in ['/hls2/', '/hls/', '/stream/', '/play/'])):
                            captured.add(cs)
                            if _is_manifest_url(cs):
                                manifest = cs
                    except Exception:
                        pass

                    time.sleep(1)

                # Final pass: read any captured manifest body
                content = None
                if manifest and manifest in manifest_bodies:
                    content = manifest_bodies[manifest]
                elif manifest_bodies:
                    content = next((v for v in manifest_bodies.values()
                                   if v and '#EXTM3U' in v), None)

                browser.close()

                if manifest:
                    if content and '#EXTM3U' in content:
                        return manifest, content
                    # Fallback: verify out-of-session (may fail on TTL).
                    try:
                        import requests
                        r = requests.get(
                            manifest,
                            headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                                              'Chrome/120.0.0.0 Safari/537.36',
                                'Referer': embed_origin + '/',
                                'Origin': embed_origin,
                            },
                            timeout=15,
                        )
                        if r.status_code == 200 and '#EXTM3U' in r.text:
                            return manifest, r.text
                    except Exception:
                        pass
                    # Return what we have (URL only) so the caller can retry.
                    return manifest, content

                # No HLS manifest found — try a direct video file
                # (VideoJS / DoodStream / generic mp4 players).
                vid = _first_video_file(captured)
                if vid:
                    return vid, None
        except Exception as e:
            last_err = e
            continue

    if last_err:
        print(f"[BrowserResolver] Failed for {embed_url}: {last_err}")
    return None


def resolve_embed_via_browser(embed_url: str, referer: str = None, cookies: list = None,
                               timeout_ms: int = 15000) -> Optional[str]:
    """
    Open an embed video page in a headless Chromium browser and capture
    the actual video URL (m3u8/mp4) that loads via JavaScript.

    Returns the first captured m3u8/mp4 URL, or None if nothing found.
    """
    result = capture_hls_manifest(embed_url, referer=referer, cookies=cookies,
                                  timeout_ms=timeout_ms)
    if isinstance(result, tuple):
        return result[0]
    return result


async def get_mp4_via_browser(url: str) -> str:
    """
    Physically opens the Akwam download page in a headless browser,
    waits for the countdown, and forcefully clicks the download button
    to bypass ad overlays and capture the final .mp4 link.
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()

            mp4_url = None

            def handle_request(req):
                nonlocal mp4_url
                if ".mp4" in req.url and "thumb" not in req.url:
                    mp4_url = req.url
            page.on("request", handle_request)

            async def handle_popup(popup):
                nonlocal mp4_url
                if ".mp4" in popup.url:
                    mp4_url = popup.url
            page.on("popup", handle_popup)

            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for button
            try:
                await page.wait_for_selector('a.download, a:has-text("تحميل")', timeout=10000)
                btn = await page.query_selector('a.download, a:has-text("تحميل")')
                if btn:
                    # Double click to bypass transparent ad overlay
                    try:
                        await btn.click(force=True)
                        await page.wait_for_timeout(500)
                        await btn.click(force=True)
                    except Exception:
                        pass
                    
                    # Wait for capture
                    for _ in range(10):
                        if mp4_url:
                            break
                        await page.wait_for_timeout(500)
                        
                        href = await btn.get_attribute('href')
                        if href and '.mp4' in href:
                            mp4_url = href
                            break
            except Exception:
                pass

            await browser.close()
            return mp4_url
    except Exception as e:
        print(f"Browser extraction failed for {url}: {e}")
        return None
