import re, requests, html as html_mod, time
from urllib.parse import unquote, urlparse

WP_API = 'https://faselhd.rip/wp-json/wp/v2'
AJAX_URL = 'https://faselhd.rip/wp-content/themes/timemovies/ajax.php'
SITE_URL = 'https://faselhd.rip'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': SITE_URL,
}

CLIENT = None  # Lazy-init cloudscraper

def _get_client():
    global CLIENT
    if CLIENT is None:
        try:
            import cloudscraper
            CLIENT = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
                delay=2,
            )
        except ImportError:
            CLIENT = requests
    return CLIENT

def safe_get(url, **kwargs):
    kwargs.setdefault('headers', HEADERS)
    kwargs.setdefault('timeout', 15)
    client = _get_client()
    try:
        return client.get(url, **kwargs)
    except Exception:
        if client is not requests:
            return requests.get(url, **kwargs)
        raise

def safe_post(url, data, **kwargs):
    kwargs.setdefault('headers', HEADERS)
    kwargs.setdefault('timeout', 15)
    return requests.post(url, data=data, **kwargs)

def decode_title(slug):
    try:
        return unquote(slug).replace('-', ' ')
    except:
        return slug.replace('-', ' ')

def detect_type(title, slug, categories):
    title_lower = title.lower()
    slug_lower = slug.lower()
    cat_names = [c.get('name', '') for c in categories] if categories else []

    is_episode = any(x in title_lower or x in slug_lower
                     for x in ['الحلقة', 'episode', ' الموسم '])
    is_movie = any(x in title_lower or x in slug_lower
                   for x in ['فيلم', 'movie', 'film'])
    is_series = any(x in title_lower or x in slug_lower
                    for x in ['مسلسل', 'series'])

    for c in cat_names:
        if 'فيلم' in c or 'movie' in c.lower():
            return 'movie' if not is_episode else 'episode'
        if 'مسلسل' in c or 'series' in c.lower():
            return 'series' if not is_episode else 'episode'

    if is_episode:
        return 'episode'
    if is_movie:
        return 'movie'
    if is_series:
        return 'series'
    return 'movie'

class FaselhdAPI:
    def search(self, query, page=1):
        url = f'{WP_API}/posts?search={query}&page={page}&per_page=20&_embed=1'
        try:
            r = safe_get(url)
            posts = r.json()
        except:
            return []

        results = []
        for p in posts:
            title = p.get('title', {}).get('rendered', '')
            slug = p.get('slug', '')
            post_id = p.get('id')
            link = p.get('link', '')
            excerpt = p.get('excerpt', {}).get('rendered', '')

            categories = []
            terms = p.get('_embedded', {}).get('wp:term', [])
            for term_group in terms:
                for term in term_group:
                    categories.append({'id': term.get('id'), 'name': term.get('name')})

            thumb = None
            media = p.get('_embedded', {}).get('wp:featuredmedia', [])
            if media:
                thumb = media[0].get('source_url') or (media[0].get('media_details', {}) or {}).get('sizes', {}).get('medium', {}).get('source_url')

            item_type = detect_type(title, slug, categories)

            results.append({
                'id': post_id,
                'name': title,
                'url': link,
                'slug': slug,
                'type': item_type,
                'thumbnail': thumb,
                'excerpt': excerpt,
                'categories': categories,
                'source': 'faselhd',
            })

        return results

    def get_categories(self):
        url = f'{WP_API}/categories?per_page=50&hide_empty=1'
        try:
            r = safe_get(url)
            cats = r.json()
        except:
            return []

        results = []
        for c in cats:
            results.append({
                'id': c.get('id'),
                'name': c.get('name'),
                'slug': c.get('slug'),
                'count': c.get('count'),
                'parent': c.get('parent', 0),
            })
        return results

    def get_category_posts(self, cat_id, page=1):
        url = f'{WP_API}/posts?categories={cat_id}&page={page}&per_page=20&_embed=1'
        try:
            r = safe_get(url)
            posts = r.json()
        except:
            return []

        results = []
        for p in posts:
            title = p.get('title', {}).get('rendered', '')
            slug = p.get('slug', '')
            thumb = None
            media = p.get('_embedded', {}).get('wp:featuredmedia', [])
            if media:
                thumb = media[0].get('source_url')

            results.append({
                'id': p.get('id'),
                'name': title,
                'url': p.get('link'),
                'slug': slug,
                'thumbnail': thumb,
                'source': 'faselhd',
            })

        return results

    def get_post_detail(self, post_id):
        url = f'{WP_API}/posts/{post_id}?_embed=1'
        try:
            r = safe_get(url)
            p = r.json()
        except:
            return None

        title = p.get('title', {}).get('rendered', '')
        slug = p.get('slug', '')
        content = p.get('content', {}).get('rendered', '')
        link = p.get('link', '')

        categories = []
        terms = p.get('_embedded', {}).get('wp:term', [])
        for term_group in terms:
            for term in term_group:
                categories.append({'id': term.get('id'), 'name': term.get('name')})

        thumb = None
        media = p.get('_embedded', {}).get('wp:featuredmedia', [])
        if media:
            thumb = media[0].get('source_url') or (media[0].get('media_details', {}) or {}).get('sizes', {}).get('medium', {}).get('source_url')

        item_type = detect_type(title, slug, categories)

        servers = self._get_servers(post_id, link)

        return {
            'id': post_id,
            'title': title,
            'slug': slug,
            'content': content,
            'thumbnail': thumb,
            'type': item_type,
            'categories': categories,
            'servers': servers,
        }

    def _get_servers(self, post_id, page_url=None):
        """Get embed servers for a FaselHD post.

        The theme loads servers via AJAX using a POST_ID that differs from
        the WordPress post ID. We first fetch the page to extract the real
        POST_ID, then call ajax.php. Falls back to extracting embed URLs
        directly from the page HTML, and finally to the govid download page.
        """
        # Step 1: fetch the post page to extract the real POST_ID
        real_post_id = str(post_id)
        govid_dl_url = None
        page_html = None

        if page_url:
            try:
                r = safe_get(page_url)
                page_html = r.content.decode('utf-8', errors='replace')

                pid_match = re.search(r'var\s+POST_ID\s*=\s*(\d+)', page_html)
                if pid_match:
                    real_post_id = pid_match.group(1)

                govid_match = re.search(r'href="(https?://govid\.\w+/d/\d+/)"', page_html)
                if govid_match:
                    govid_dl_url = govid_match.group(1)
            except Exception:
                pass

        servers = []
        seen_urls = set()

        # Step 2: Try AJAX to get server iframes
        for idx in range(15):
            try:
                r = safe_post(AJAX_URL, {'post_id': real_post_id, 'server': str(idx)})
                data = r.json()
                if not data.get('success'):
                    if idx == 0:
                        continue
                    break
                iframe_html = data.get('iframe', '')
                srcs = re.findall(r'src=["\']([^"\']+)["\']', iframe_html)
                src = srcs[0] if srcs else None
                if src and src not in seen_urls:
                    seen_urls.add(src)
                    servers.append({
                        'index': idx,
                        'name': f'Server {idx + 1}',
                        'embed_url': src,
                        'post_id': int(real_post_id),
                    })
            except:
                if idx > 0:
                    break

        # Step 3: Fallback — extract embed URLs directly from page HTML
        if not servers and page_html:
            for src in re.findall(
                r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']',
                page_html, re.IGNORECASE
            ):
                if 'govid' not in src and 'faselhd' not in src and src not in seen_urls:
                    seen_urls.add(src)
                    servers.append({
                        'index': len(servers),
                        'name': f'Server {len(servers) + 1}',
                        'embed_url': src,
                        'post_id': int(real_post_id),
                    })
            if not servers:
                video_hosts = [
                    'uqload', 'dood', 'streamtape', 'voe', 'mixdrop', 'filemoon',
                    'vidoza', 'upstream', 'streamlare', 'miiiixdrop', 'playmogo',
                    'fastvid', 'vinovo', 'hglink', 'callistanise', 'dhcplay',
                    'lulustream', 'vidspeed', 'vidoba', 'fastved',
                ]
                for host in video_hosts:
                    for m in re.finditer(
                        rf'''href=["'](https?://[^"']*{re.escape(host)}[^"']+)["']''',
                        page_html, re.IGNORECASE
                    ):
                        url = m.group(1)
                        if url not in seen_urls:
                            seen_urls.add(url)
                            servers.append({
                                'index': len(servers),
                                'name': f'Server {len(servers) + 1} ({host})',
                                'embed_url': url,
                                'post_id': int(real_post_id),
                            })
                            break

        # Step 4: Always add the govid download page as a server fallback
        if govid_dl_url and govid_dl_url not in seen_urls:
            name = f'Server {len(servers) + 1}'
            servers.append({
                'index': len(servers),
                'name': f'{name} (Download)',
                'embed_url': govid_dl_url,
                'post_id': int(real_post_id),
            })

        # Step 5: Fallback — extract any direct .mp4/.m3u8 URLs from page HTML
        if not servers and page_html:
            for m in re.finditer(
                r'(https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)[^\s"\'<>]*)',
                page_html
            ):
                url = m.group(1)
                if 'faselhd' not in url:
                    servers.append({
                        'index': len(servers),
                        'name': f'Server {len(servers) + 1} (Direct)',
                        'embed_url': url,
                        'post_id': int(real_post_id),
                    })
                    break  # Just take the first direct URL

        return servers

    def resolve_govid_embed(self, embed_url, post_id):
        """Try to resolve a govid embed URL to a video URL.

        govid now uses Cloudflare Turnstile, so server-side resolution
        is limited. We try a few patterns but fall back to returning
        the embed URL as-is (the browser will handle Turnstile).
        """
        try:
            # Try the /d/ page format (more stable than /play/)
            d_url = embed_url
            if '/play/' in d_url:
                # Convert /play/... to /d/{post_id}/
                if post_id:
                    d_url = f'https://govid.live/d/{post_id}/'

            # Try to fetch the page and look for video URLs
            try:
                r = safe_get(d_url, headers={**HEADERS, 'Referer': 'https://faselhd.rip/'}, timeout=10)
                if r is not None:
                    html = r.text
                    # Look for direct video URLs
                    for m in re.finditer(
                        r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)',
                        html
                    ):
                        return {'url': m.group(1), 'type': 'hls' if '.m3u8' in m.group(1) else 'mp4'}
            except Exception:
                pass

            # Fallback: return the embed URL for browser-based resolution
            return {'url': embed_url, 'type': 'embed'}
        except:
            return None

    def resolve_embed(self, embed_url):
        try:
            with __import__('yt_dlp').YoutubeDL({
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'nocheckcertificate': True,
            }) as ydl:
                info = ydl.extract_info(embed_url, download=False)
                if not info:
                    return None

                formats = info.get('formats', [])
                best = None
                combined = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                if combined:
                    best = max(combined, key=lambda f: f.get('height', 0) or 0)
                if not best:
                    video = [f for f in formats if f.get('vcodec') != 'none']
                    if video:
                        best = max(video, key=lambda f: f.get('height', 0) or 0)
                if not best and formats:
                    best = formats[0]

                return {
                    'url': best.get('url') if best else info.get('url'),
                    'title': info.get('title'),
                    'ext': info.get('ext', 'mp4'),
                    'quality': f"{best.get('height', 0)}p" if best and best.get('height') else None,
                    'filesize': best.get('filesize') if best else None,
                    'formats': [{'url': f.get('url'), 'ext': f.get('ext'),
                                 'quality': f.get('format_note', '')}
                                for f in formats if f.get('url')] if formats else None,
                }
        except Exception as e:
            pass

        # Fallback: VideoResolver (yt-dlp → streamlink → HTML scrape → browser)
        try:
            from .video_resolver import VideoResolver
            resolved = VideoResolver()._resolve_sync(embed_url)
            if resolved:
                return {
                    'url': resolved.url,
                    'title': resolved.title,
                    'ext': resolved.ext,
                    'quality': resolved.quality,
                    'filesize': resolved.filesize,
                }
        except Exception:
            pass
        return None

    def get_series_structure(self, series_slug):
        series_slug_clean = series_slug.replace('-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85', '')
        series_slug_clean = re.sub(r'%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-\d+.*', '', series_slug_clean)
        series_slug_clean = re.sub(r'-\d{4}.*', '', series_slug_clean)
        series_slug_clean = series_slug_clean.rstrip('-')

        search_query = series_slug.replace('-', ' ').replace('+', ' ')
        from urllib.parse import quote
        search_query_encoded = quote(search_query, safe='')

        search_url = f'{WP_API}/posts?search={search_query_encoded}&per_page=100&_embed=1'
        try:
            r = safe_get(search_url)
            all_posts = r.json()
        except:
            return None

        if not all_posts or isinstance(all_posts, dict):
            return None

        title = all_posts[0].get('title', {}).get('rendered', '')
        thumb = None
        media = all_posts[0].get('_embedded', {}).get('wp:featuredmedia', [])
        if media:
            thumb = media[0].get('source_url')

        episodes = []
        for p in all_posts:
            post_title = p.get('title', {}).get('rendered', '')
            post_slug = p.get('slug', '')
            link = p.get('link', '')
            pid = p.get('id')

            season_num = 1
            ep_num = 0

            season_match = re.search(r'%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-%d8%a7%d9%84(%d8%a7%d9%88%d9%84|%d8%ab%d8%a7%d9%86%d9%8a|%d8%ab%d8%a7%d9%84%d8%ab)', post_slug)
            if not season_match:
                season_match = re.search(r'mawsim-(\d+)', post_slug, re.I)
            if not season_match:
                season_match = re.search(r' season[-\s]*(\d+)', post_slug, re.I)

            if season_match:
                season_text = season_match.group(1)
                season_map = {
                    '%d8%a7%d9%84%d8%a7%d9%88%d9%84': 1,
                    '%d8%ab%d8%a7%d9%86%d9%8a': 2,
                    '%d8%ab%d8%a7%d9%84%d8%ab': 3,
                }
                season_num = season_map.get(season_text, int(season_text) if season_text.isdigit() else 1)

            ep_match = re.search(r'%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-(\d+)', post_slug)
            if ep_match:
                ep_num = int(ep_match.group(1))

            episodes.append({
                'id': pid,
                'title': post_title,
                'url': link,
                'season': season_num,
                'episode': ep_num,
            })

        episodes.sort(key=lambda x: (x['season'], x['episode']))

        seasons = {}
        for ep in episodes:
            s = ep['season']
            if s not in seasons:
                seasons[s] = []
            seasons[s].append({
                'episode': ep['episode'],
                'title': ep['title'],
                'url': ep['url'],
                'id': ep['id'],
            })

        result = {
            'title': title,
            'thumbnail': thumb,
            'seasons': [],
        }
        for s_num in sorted(seasons.keys()):
            result['seasons'].append({
                'season_number': s_num,
                'episodes': seasons[s_num],
            })

        return result

    def extract_series_info(self, title, slug):
        series_name = title
        ep_num = None
        season_num = 1

        ep_match = re.search(r'%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-(\d+)', slug)
        if ep_match:
            ep_num = int(ep_match.group(1))
            series_name = re.sub(r'\s*%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-\d+.*', '', slug)

        season_match = re.search(r'%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-%d8%a7%d9%84(%d8%a7%d9%88%d9%84|%d8%ab%d8%a7%d9%86%d9%8a|%d8%ab%d8%a7%d9%84%d8%ab)', slug)
        if season_match:
            season_text = season_match.group(1)
            season_map = {
                '%d8%a7%d9%84%d8%a7%d9%88%d9%84': 1,
                '%d8%ab%d8%a7%d9%86%d9%8a': 2,
                '%d8%ab%d8%a7%d9%84%d8%ab': 3,
            }
            season_num = season_map.get(season_text, 1)
            series_name = re.sub(r'-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-%d8%a7%d9%84\w+.*', '', slug)

        return series_name, season_num, ep_num

    def get_trending(self):
        try:
            r = safe_get(SITE_URL)
            html = r.text
        except:
            return []

        results = []
        cards = re.findall(r'<div[^>]*class="[^"]*hero-card[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.DOTALL)

        if not cards:
            links = re.findall(r'<a[^>]*href="(https?://faselhd\.rip/[^"]+)"[^>]*class="[^"]*show-card[^"]*"[^>]*>', html)
            seen = set()
            for link in links:
                if link not in seen:
                    seen.add(link)
                    slug = link.rstrip('/').split('/')[-1]
                    results.append({
                        'name': slug.replace('-', ' ').title(),
                        'url': link,
                        'slug': slug,
                        'source': 'faselhd',
                    })
            return results[:20]

        for card in cards:
            title_m = re.search(r'card-title[^>]*>([^<]+)', card)
            link_m = re.search(r'href="([^"]+)"', card)
            if title_m and link_m:
                slug = link_m.group(1).rstrip('/').split('/')[-1]
                results.append({
                    'name': html_mod.unescape(title_m.group(1).strip()),
                    'url': link_m.group(1),
                    'slug': slug,
                    'source': 'faselhd',
                })

        return results[:20]
