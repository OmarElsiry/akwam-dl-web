const Sahid4uWorker = (() => {
    const BASE_URL = 'https://shhahhid4u.com';

    const CORS_PROXIES = [
        (url) => `/api/cors-proxy?url=${encodeURIComponent(url)}`,
        (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
        (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    ];

    let workingProxyIndex = 0;

    function isChallengePage(html) {
        // A successful page can still include Cloudflare's passive JSD
        // telemetry script. Only reject markup that represents a real block.
        return /<title[^>]*>\s*(?:Just a moment|Attention Required)|id=["']cf-error-details["']|class=["'][^"']*(?:cf-turnstile|challenge-form)[^"']*["']|id=["']challenge-(?:form|stage|running)["']/i.test(html || '');
    }

    async function corsFetch(url) {
        let lastError = null;
        const indices = [workingProxyIndex];
        for (let i = 0; i < CORS_PROXIES.length; i++) {
            if (i !== workingProxyIndex) indices.push(i);
        }
        for (const idx of indices) {
            const proxyFn = CORS_PROXIES[idx];
            const proxiedUrl = proxyFn(url);
            try {
                const resp = await fetch(proxiedUrl, {
                    headers: { Accept: 'text/html,application/xhtml+xml,*/*' },
                    signal: AbortSignal.timeout(8000),
                });
                if (!resp.ok) {
                    lastError = new Error(`HTTP ${resp.status}`);
                    continue;
                }
                const text = await resp.text();
                if (isChallengePage(text)) {
                    lastError = new Error('Provider challenge page');
                    continue;
                }
                if (workingProxyIndex !== idx) workingProxyIndex = idx;
                return text;
            } catch (err) {
                lastError = err;
                continue;
            }
        }
        throw lastError || new Error('All CORS proxies failed');
    }

    function extractNameFromInner(inner, href) {
        // 1. Try <p> with title class (sahid4u search cards use this)
        const pTitle = inner.match(/<p[^>]*class=["'][^"']*title[^"']*["'][^>]*>([\s\S]*?)<\/p>/i);
        if (pTitle) return pTitle[1].replace(/<[^>]+>/g, '').trim();
        // 2. Try <h3> or <h2>
        const hMatch = inner.match(/<(h[23])[^>]*>([\s\S]*?)<\/\1>/i);
        if (hMatch) return hMatch[2].replace(/<[^>]+>/g, '').trim();
        // 3. Try <span> with title/name class
        const spanMatch = inner.match(/<span[^>]*class=["'][^"']*(?:title|name)[^"']*["'][^>]*>([\s\S]*?)<\/span>/i);
        if (spanMatch) return spanMatch[1].replace(/<[^>]+>/g, '').trim();
        // 4. Try image alt attribute
        const altMatch = inner.match(/alt=(["'])([^"']+)\1/i);
        if (altMatch) return altMatch[2];
        // 5. Try link title attribute
        const titleMatch = inner.match(/title=(["'])([^"']+)\1/i);
        if (titleMatch) return titleMatch[2];
        // 6. Get first short meaningful text snippet
        const allText = inner.replace(/<[^>]+>/g, '').trim();
        const lines = allText.split(/\n+/).map(l => l.trim()).filter(l => l.length > 3);
        if (lines.length > 0) return lines[0];
        // 7. Fallback: URL slug
        return href.split('/').pop().replace(/[-_]/g, ' ');
    }

    function extractAllLinks(html) {
        const links = [];
        const pattern = /<a[^>]+href=(["'])([^"']+)\1[^>]*>([\s\S]*?)<\/a>/gi;
        let match;
        while ((match = pattern.exec(html)) !== null) {
            let href = match[2].trim();
            const inner = match[3].trim();
            const name = extractNameFromInner(inner, href);
            const allText = inner.replace(/<[^>]+>/g, '').trim();
            if (href.startsWith('/')) href = BASE_URL + href;
            if (!href.startsWith('http')) continue;
            links.push({ href, name, text: allText });
        }
        return links;
    }

    function filterByPath(links, pathSegment) {
        return links.filter((l) => l.href.includes(pathSegment));
    }

    function extractTitle(html) {
        const meta = html.match(
            /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i
        );
        if (meta) return meta[1];
        const h1 = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
        if (h1) return h1[1].replace(/<[^>]+>/g, '').trim();
        const title = html.match(/<title>([^<]*)<\/title>/i);
        if (title) return title[1].trim();
        return null;
    }

    // Clean up a name: remove Arabic prefixes like مسلسل, فيلم, الحلقة, الموسم
    function cleanName(name) {
        if (!name) return name;
        return name
            .replace(/مسلسل|فيلم|انمي|مترجم|مترجمة|مدبلج|مدبلجة|اون لاين/gi, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    // ── Search ───────────────────────────────────────────────
    async function search(query) {
        const q = encodeURIComponent(query.trim());
        const url = `${BASE_URL}/search?s=${q}`;
        const html = await corsFetch(url);
        const links = extractAllLinks(html);
        const seen = new Set();
        const results = [];

        for (const link of links) {
            let type = null;
            if (link.href.includes('/film/')) type = 'movie';
            else if (link.href.includes('/series/')) type = 'series';
            else if (link.href.includes('/episode/')) type = 'episode';
            else continue;
            if (seen.has(link.href)) continue;
            seen.add(link.href);

            // Episode page names are in the <a> inner text
            // Try to get a clean name by looking for a span or h3 within
            let name = link.name;
            if (!name || name.length < 3) {
                const slug = link.href.split('/').pop();
                name = decodeURIComponent(slug)
                    .replace(/[-_]/g, ' ')
                    .replace(/مسلسل |فيلم |انمي /g, '')
                    .trim();
            }

            results.push({ name, url: link.href, type, source: 'sahid4u' });
        }
        return results;
    }

    // ── Seasons ──────────────────────────────────────────────
    async function getSeasons(seriesUrl) {
        const html = await corsFetch(seriesUrl);
        const links = extractAllLinks(html);
        const seasonLinks = filterByPath(links, '/season/');
        const seen = new Set();
        return seasonLinks
            .filter((l) => {
                if (seen.has(l.href)) return false;
                seen.add(l.href);
                return true;
            })
            .map((l) => ({ name: l.name || 'Season', url: l.href }));
    }

    // ── Episodes ─────────────────────────────────────────────
    async function getEpisodes(seasonUrl) {
        const html = await corsFetch(seasonUrl);
        const links = extractAllLinks(html);
        const episodeLinks = filterByPath(links, '/episode/');
        const seen = new Set();
        return episodeLinks
            .filter((l) => {
                if (seen.has(l.href)) return false;
                seen.add(l.href);
                return true;
            })
            .map((l) => ({ name: l.name || 'Episode', url: l.href }));
    }

    // ── Extract series info from an episode page ────────────
    async function getEpisodeSeriesInfo(episodeUrl) {
        const html = await corsFetch(episodeUrl);
        const links = extractAllLinks(html);
        const seriesLinks = filterByPath(links, '/series/');
        const seasonLinks = filterByPath(links, '/season/');
        return {
            series: seriesLinks.length > 0 ? { name: seriesLinks[0].name, url: seriesLinks[0].href } : null,
            season: seasonLinks.length > 0 ? { name: seasonLinks[0].name, url: seasonLinks[0].href } : null,
        };
    }

    // ── Content Info ─────────────────────────────────────────
    async function getContentInfo(contentUrl) {
        const html = await corsFetch(contentUrl);
        const links = extractAllLinks(html);
        const title = extractTitle(html);
        const watchUrls = filterByPath(links, '/watch/').map((l) => l.href);
        const downloadUrls = filterByPath(links, '/download/').map((l) => l.href);

        // Try to get a cleaner name
        let name = title;
        if (!name) {
            const h3 = html.match(/<h3[^>]*class=["'][^"']*title[^"']*["'][^>]*>([\s\S]*?)<\/h3>/i);
            if (h3) name = h3[1].replace(/<[^>]+>/g, '').trim();
        }

        return {
            title: cleanName(name || ''),
            watchUrl: watchUrls.length > 0 ? watchUrls[0] : null,
            downloadUrl: downloadUrls.length > 0 ? downloadUrls[0] : null,
        };
    }

    // ── Watch Servers ────────────────────────────────────────
    async function getWatchServers(watchUrl) {
        const html = await corsFetch(watchUrl);
        const normalizeServers = (servers) => servers.map((s) => ({
            name: s.name || 'Server',
            url: s.url || '',
            id: s.id,
        }));
        const rawMatch = html.match(/let\s+rawServers\s*=\s*(\[[\s\S]*?\]);/i);
        if (rawMatch) {
            try {
                return normalizeServers(JSON.parse(rawMatch[1]));
            } catch (e) {
                console.error('[Sahid4uWorker] rawServers parse failed:', e);
            }
        }
        const nestedMatch = html.match(/let\s+servers\s*=\s*JSON\.parse\(\s*(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)')\s*\)\s*;/i);
        if (nestedMatch) {
            try {
                const payload = nestedMatch[1] !== undefined
                    ? JSON.parse('"' + nestedMatch[1] + '"')
                    : nestedMatch[2].replace(/\\'/g, "'");
                return normalizeServers(JSON.parse(payload));
            } catch (e) {
                console.error('[Sahid4uWorker] nested servers parse failed:', e);
            }
        }
        const iframeMatch = html.match(/<iframe[^>]+src=["']([^"']+)["']/i);
        if (iframeMatch) {
            return [{ name: 'Embed', url: iframeMatch[1] }];
        }
        return [];
    }

    // ── Download / Quality Info ─────────────────────────────
    // The /download/{slug} page shows available qualities but NOT actual
    // download server links. We extract quality info for display purposes.
    async function getDownloadInfo(downloadUrl) {
        const html = await corsFetch(downloadUrl);

        // Extract quality badges from the page
        // Pattern: <a href="/quality/720p WEB-DL" class="btn btn-gray mb-2 ms-2">720p WEB-DL</a>
        const qualityMatches = html.matchAll(
            /<a[^>]*href=["']\/quality\/([^"']+)["'][^>]*class=["'][^"']*btn-gray[^"']*["'][^>]*>([\s\S]*?)<\/a>/gi
        );
        const qualities = [];
        for (const m of qualityMatches) {
            const name = m[2].replace(/<[^>]+>/g, '').trim();
            if (name) qualities.push(name);
        }

        return qualities;
    }

    // ── Get all servers + download info ─────────────────────
    async function getContentServersAndDownloads(contentUrl) {
        let watchUrl = null;
        let downloadUrl = null;
        const slugMatch = contentUrl.match(/\/(film|episode)\/([^/?#]+)/);
        if (slugMatch) {
            const slug = slugMatch[2];
            watchUrl = `${BASE_URL}/watch/${slug}`;
            downloadUrl = `${BASE_URL}/download/${slug}`;
        }
        try {
            const info = await getContentInfo(contentUrl);
            if (info.watchUrl) watchUrl = info.watchUrl;
            if (info.downloadUrl) downloadUrl = info.downloadUrl;
        } catch (e) {
            console.warn('[Sahid4uWorker] getContentInfo failed:', e);
        }

        let servers = [];
        let qualities = [];
        const tasks = [];
        if (watchUrl)
            tasks.push(
                getWatchServers(watchUrl)
                    .then((s) => { servers = s; })
                    .catch(() => {})
            );
        if (downloadUrl)
            tasks.push(
                getDownloadInfo(downloadUrl)
                    .then((q) => { qualities = q; })
                    .catch(() => {})
            );
        await Promise.all(tasks);
        return { servers, qualities, watchUrl, downloadUrl };
    }

    // ── Public API ────────────────────────────────────────────
    return {
        search,
        getSeasons,
        getEpisodes,
        getContentInfo,
        getEpisodeSeriesInfo,
        getWatchServers,
        getDownloadInfo,
        getContentServersAndDownloads,
        corsFetch,
    };
})();
