// ============================================================
//  AkwamWorker — Client-Side Akwam Engine
//  All Akwam fetching & parsing runs in the USER's browser.
//  The server is never involved — Akwam sees each user's own IP.
// ============================================================

const AkwamWorker = (() => {
    // ── Config ────────────────────────────────────────────────
    const ENTRY_URL = 'https://ak.sv/';
    let BASE_URL = null; // Resolved on first use

    // Regex patterns (ported from akwam_api.py)
    const RGX_QUALITY_TAG = /data-quality="\d+".*?href="https?:\/\/([^"]+\/link\/\d+)"/g;
    const RGX_SIZE_TAG    = /font-size-14 mr-auto">([0-9.MGB ]+)<\//g;
    const RGX_SHORTEN_URL = /https?:\/\/(\w*\.*\w+\.\w+\/download\/.*?)"/g;
    const RGX_DIRECT_URL  = /([a-z0-9]{4,}\.\w+\.\w+\/download\/.*?)"/g;

    // ── CORS Proxy Chain ──────────────────────────────────────
    // Each user's browser tries these in order. Public proxies
    // handle 90%+ of traffic; server fallback catches the rest.
    const CORS_PROXIES = [
        // 1. corsproxy.io — fast, reliable
        (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
        // 2. allorigins — returns JSON wrapper with contents field
        (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
        // 3. Server fallback — dumb pipe, no parsing
        (url) => `/api/cors-proxy?url=${encodeURIComponent(url)}`,
    ];

    /**
     * Fetch a URL through the CORS proxy chain.
     * Tries each proxy in order until one succeeds.
     * Returns the raw HTML text.
     */
    async function corsFetch(url) {
        let lastError = null;
        for (const proxyFn of CORS_PROXIES) {
            const proxiedUrl = proxyFn(url);
            try {
                const resp = await fetch(proxiedUrl, {
                    headers: {
                        'Accept': 'text/html,application/xhtml+xml,*/*',
                    },
                    signal: AbortSignal.timeout(25000),
                });
                if (!resp.ok) {
                    lastError = new Error(`HTTP ${resp.status} from proxy`);
                    continue;
                }
                return await resp.text();
            } catch (err) {
                lastError = err;
                continue;
            }
        }
        throw lastError || new Error('All CORS proxies failed');
    }

    /**
     * Resolve Akwam's actual base URL from the short URL (ak.sv → akwam.com.co etc)
     * Done once per session, cached.
     */
    async function resolveBaseUrl() {
        if (BASE_URL) return BASE_URL;
        try {
            const html = await corsFetch(ENTRY_URL);
            // Extract canonical or og:url to find the real domain
            const canonical = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i);
            if (canonical) {
                let u = canonical[1];
                if (u.endsWith('/')) u = u.slice(0, -1);
                BASE_URL = u.replace(/\/[^/]*$/, '').replace(/\/$/, '');
                // If canonical gives just a page URL, extract the origin
                try {
                    const parsed = new URL(u);
                    BASE_URL = parsed.origin;
                } catch {}
            }
            if (!BASE_URL) {
                // Fallback: look for akwam domain in the HTML
                const domainMatch = html.match(/https?:\/\/((?:www\.)?akwam\.[a-z.]+)/i);
                if (domainMatch) {
                    BASE_URL = 'https://' + domainMatch[1];
                }
            }
            if (!BASE_URL) {
                // Hardcoded fallback
                BASE_URL = 'https://akwam.to';
            }
        } catch {
            BASE_URL = 'https://akwam.to';
        }
        // Remove trailing slash
        if (BASE_URL.endsWith('/')) BASE_URL = BASE_URL.slice(0, -1);
        console.log('[AkwamWorker] Resolved base URL:', BASE_URL);
        return BASE_URL;
    }

    // ── Search ────────────────────────────────────────────────
    async function search(query, type = 'movie') {
        const base = await resolveBaseUrl();
        const q = query.replace(/ /g, '+');
        const url = `${base}/search?q=${q}&section=${type}&page=1`;
        const html = await corsFetch(url);

        // Pattern: find all movie/series URLs
        const pattern = new RegExp(`(${escapeRegex(base)}/${type}/\\d+/[^"\\s]+)`, 'g');
        const matches = [...html.matchAll(pattern)];

        const results = [];
        const seen = new Set();
        for (const m of matches) {
            const matchUrl = m[1];
            if (seen.has(matchUrl)) continue;
            seen.add(matchUrl);
            const name = matchUrl.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            results.push({ name, url: matchUrl, source: 'akwam' });
        }
        return results;
    }

    // ── Episodes ──────────────────────────────────────────────
    async function getEpisodes(seriesUrl) {
        const base = await resolveBaseUrl();
        const html = await corsFetch(seriesUrl);

        const pattern = new RegExp(`(${escapeRegex(base)}/episode/\\d+[^"\\s]*)`, 'g');
        const matches = [...html.matchAll(pattern)];

        const episodes = [];
        const seen = new Set();
        for (const m of matches) {
            const epUrl = m[1];
            if (seen.has(epUrl)) continue;
            seen.add(epUrl);
            const name = epUrl.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            episodes.push({ name, url: epUrl });
        }
        // Reverse to chronological order
        return episodes.reverse();
    }

    // ── Qualities ─────────────────────────────────────────────
    async function getQualities(contentUrl) {
        const html = await corsFetch(contentUrl);
        const singleLine = html.replace(/\n/g, '');

        // Extract quality link_ids
        const qualityPattern = /data-quality="\d+".*?href="https?:\/\/([^"]+\/link\/\d+)"/g;
        const qualityMatches = [...singleLine.matchAll(qualityPattern)];
        const uniqueLinks = [];
        for (const m of qualityMatches) {
            if (!uniqueLinks.includes(m[1])) uniqueLinks.push(m[1]);
        }

        // Extract sizes
        const sizePattern = /font-size-14 mr-auto">([0-9.MGB ]+)<\//g;
        const sizeMatches = [...singleLine.matchAll(sizePattern)];

        // Match quality labels to links
        const qLabels = ['1080p', '720p', '480p', '360p', '240p'];
        const qualities = [];
        let idx = 0;
        for (const q of qLabels) {
            if (html.includes(`>${q}</`) && idx < uniqueLinks.length) {
                const size = idx < sizeMatches.length ? sizeMatches[idx][1] : 'Unknown';
                qualities.push({
                    quality: q,
                    link_id: uniqueLinks[idx],
                    size: size
                });
                idx++;
            }
        }
        return qualities;
    }

    // ── Resolve Direct URL ────────────────────────────────────
    // Replicates resolve_direct_url from akwam_api.py
    async function resolveDirectUrl(linkIdUrl) {
        const url = 'https://' + linkIdUrl;
        let html;
        try {
            html = await corsFetch(url);
        } catch {
            return null;
        }

        // Find all /download/ hrefs
        const dlPattern = /href="(https?:\/\/[^"]+\/download\/[^"]+)"/g;
        const dlMatches = [...html.matchAll(dlPattern)];
        const dlLinks = [];
        const seen = new Set();
        for (const m of dlMatches) {
            if (!seen.has(m[1])) {
                seen.add(m[1]);
                dlLinks.push(m[1]);
            }
        }

        if (dlLinks.length === 0) return url; // Return /link/ page as fallback

        // Try each download server
        for (const dlUrl of dlLinks) {
            try {
                const html2 = await corsFetch(dlUrl);

                // Check for .mp4 href
                const mp4 = html2.match(/href=["']([^"']+\.mp4)["']/);
                if (mp4) return mp4[1];

                // Check for .mkv href
                const mkv = html2.match(/href=["']([^"']+\.mkv)["']/);
                if (mkv) return mkv[1];
            } catch {
                continue;
            }
        }
        // Fallback: return the first download page URL
        return dlLinks[0];
    }

    // ── Resolve Stream URL ────────────────────────────────────
    // Replicates _fast_resolve_video_url from index.py
    async function resolveStream(linkId) {
        // Normalize: accept both "143994" and "go.akwam.com.co/link/143994"
        const idMatch = linkId.match(/(\d+)$/);
        if (!idMatch) return { url: null, referer: null };
        const numericId = idMatch[1];

        const base = await resolveBaseUrl();
        // Build link URL using the resolved base domain
        const domain = new URL(base).hostname;
        const linkUrl = `https://go.${domain}/link/${numericId}`;

        try {
            const html1 = await corsFetch(linkUrl);

            // Step 1: Find /download/ URL (shortened)
            const shortenPattern = /https?:\/\/(\w*\.*\w+\.\w+\/download\/.*?)"/g;
            const shortenMatches = [...html1.matchAll(shortenPattern)];
            if (shortenMatches.length === 0) return { url: null, referer: null };

            const dlUrl = 'https://' + shortenMatches[0][1];

            // Step 2: Fetch the download page
            const html2 = await corsFetch(dlUrl);

            // Step 3: Extract CDN file URL
            const directPattern = /([a-z0-9]{4,}\.\w+\.\w+\/download\/.*?)"/g;
            const directMatches = [...html2.matchAll(directPattern)];
            const cdnUrls = directMatches
                .map(m => m[1])
                .filter(m => m.includes('downet.net') || m.endsWith('.mp4') || m.endsWith('.mkv'));

            if (cdnUrls.length > 0) {
                return { url: 'https://' + cdnUrls[0], referer: dlUrl };
            }

            // Fallback: href-based patterns
            const mp4 = html2.match(/href=["']([^"']+\.mp4)["']/);
            if (mp4) return { url: mp4[1], referer: dlUrl };

            const mkv = html2.match(/href=["']([^"']+\.mkv)["']/);
            if (mkv) return { url: mkv[1], referer: dlUrl };

            return { url: null, referer: null };
        } catch {
            return { url: null, referer: null };
        }
    }

    // ── Get Download Links ────────────────────────────────────
    // Replicates get_download_links from akwam_api.py
    async function getDownloadLinks(linkIdUrl) {
        const url = 'https://' + linkIdUrl;
        try {
            const html = await corsFetch(url);
            const dlPattern = /href="(https?:\/\/[^"]+\/download\/[^"]+)"/g;
            const matches = [...html.matchAll(dlPattern)];
            const links = [];
            const seen = new Set();
            for (const m of matches) {
                if (!seen.has(m[1])) {
                    seen.add(m[1]);
                    links.push(m[1]);
                }
            }
            return links;
        } catch {
            return [];
        }
    }

    // ── Bulk Resolve ──────────────────────────────────────────
    // All episodes resolved in parallel IN THE USER'S BROWSER
    async function bulkResolve(episodes) {
        // Step 1: Get qualities for all episodes in parallel
        const allQualities = await Promise.all(
            episodes.map(ep => getQualities(ep.url).catch(() => []))
        );

        // Step 2: Resolve + get download links for each
        const tasks = [];
        for (let i = 0; i < allQualities.length; i++) {
            const qualities = allQualities[i];
            let bestQ = qualities.find(q => q.quality === '720p');
            if (!bestQ && qualities.length > 0) bestQ = qualities[0];
            if (bestQ) {
                tasks.push({
                    name: episodes[i].name,
                    quality: bestQ,
                    resolvePromise: resolveDirectUrl(bestQ.link_id).catch(() => null),
                    dlLinksPromise: getDownloadLinks(bestQ.link_id).catch(() => []),
                });
            }
        }

        // Step 3: Await all resolves in parallel
        const resolvedUrls = await Promise.all(tasks.map(t => t.resolvePromise));
        const allDlLinks   = await Promise.all(tasks.map(t => t.dlLinksPromise));

        // Step 4: Build results
        const results = [];
        for (let i = 0; i < tasks.length; i++) {
            if (resolvedUrls[i]) {
                results.push({
                    name: tasks[i].name,
                    url: resolvedUrls[i],
                    quality: tasks[i].quality.quality || '720p',
                    size: tasks[i].quality.size || '',
                    download_links: allDlLinks[i],
                });
            }
        }
        return results;
    }

    // ── Helpers ───────────────────────────────────────────────
    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // ── Public API ────────────────────────────────────────────
    return {
        search,
        getEpisodes,
        getQualities,
        resolveDirectUrl,
        resolveStream,
        getDownloadLinks,
        bulkResolve,
        resolveBaseUrl,    // Expose for debugging
        corsFetch,         // Expose for debugging
    };
})();
