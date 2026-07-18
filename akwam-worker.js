// ============================================================
//  AkwamWorker — Client-Side Akwam Engine
//  All Akwam fetching & parsing runs in the USER's browser.
//  The server is never involved — Akwam sees each user's own IP.
// ============================================================

const AkwamWorker = (() => {
    // ── Config ────────────────────────────────────────────────
    const ENTRY_URL = 'https://ak.sv/';
    let BASE_URL = null;

    // ── CORS Proxy Chain ──────────────────────────────────────
    const CORS_PROXIES = [
        (url) => `https://corsproxy.io/?${encodeURIComponent(url)}`,
        (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
        (url) => `/api/cors-proxy?url=${encodeURIComponent(url)}`,
    ];

    let workingProxyIndex = 0;

    async function corsFetch(url) {
        let lastError = null;
        const indices = [];
        indices.push(workingProxyIndex);
        for (let i = 0; i < CORS_PROXIES.length; i++) {
            if (i !== workingProxyIndex) indices.push(i);
        }
        for (const idx of indices) {
            const proxyFn = CORS_PROXIES[idx];
            const proxiedUrl = proxyFn(url);
            try {
                const resp = await fetch(proxiedUrl, {
                    headers: { 'Accept': 'text/html,application/xhtml+xml,*/*' },
                    signal: AbortSignal.timeout(8000),
                });
                if (!resp.ok) {
                    lastError = new Error(`HTTP ${resp.status} from proxy ${proxiedUrl}`);
                    continue;
                }
                const text = await resp.text();
                if (workingProxyIndex !== idx) {
                    workingProxyIndex = idx;
                }
                return text;
            } catch (err) {
                lastError = err;
                continue;
            }
        }
        throw lastError || new Error('All CORS proxies failed');
    }

    async function resolveBaseUrl() {
        if (BASE_URL) return BASE_URL;
        try {
            const html = await corsFetch(ENTRY_URL);
            const canonical = html.match(/<link[^>]+rel=["']canonical["'][^>]+href=["']([^"']+)["']/i);
            if (canonical) {
                try {
                    const parsed = new URL(canonical[1]);
                    BASE_URL = parsed.origin;
                } catch {
                    let u = canonical[1];
                    if (u.endsWith('/')) u = u.slice(0, -1);
                    BASE_URL = u.replace(/\/[^/]*$/, '').replace(/\/$/, '');
                }
            }
            if (!BASE_URL) {
                const domainMatch = html.match(/https?:\/\/((?:www\.)?akwam\.[a-z.]+)/i);
                if (domainMatch) BASE_URL = 'https://' + domainMatch[1];
            }
            if (!BASE_URL) BASE_URL = 'https://akwam.to';
        } catch {
            BASE_URL = 'https://akwam.to';
        }
        if (BASE_URL.endsWith('/')) BASE_URL = BASE_URL.slice(0, -1);
        return BASE_URL;
    }

    // ── Search ────────────────────────────────────────────────
    async function search(query, type = 'movie') {
        const base = await resolveBaseUrl();
        const q = query.replace(/ /g, '+');
        const url = `${base}/search?q=${q}&section=${type}&page=1`;
        const html = await corsFetch(url);
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
        return episodes.reverse();
    }

    // ── Qualities ─────────────────────────────────────────────
    async function getQualities(contentUrl) {
        const html = await corsFetch(contentUrl);

        // New Akwam structure: quality tabs with watch/download URLs
        //   <li><a href="#tab-4" class="selected">720p</a></li>
        //   <div class="tab-content quality" id="tab-4">
        //     <a href="https://akwam.it/watch/{id}/{movie_id}/{slug}" class="link-btn link-show">مشاهدة</a>
        //     <a href="https://akwam.it/download/{id}/{movie_id}/{slug}" class="link-btn link-download">
        //       <span class="font-size-14 mr-auto">863.1 MB</span>
        //     </a>
        //   </div>

        const tabPattern = /<a\s+href="#(tab-\d+)"[^>]*>\s*(\d+p)\s*<\/a>/g;
        const tabMatches = [...html.matchAll(tabPattern)];

        const qualities = [];

        for (const tabMatch of tabMatches) {
            const tabId = tabMatch[1];
            const qualityLabel = tabMatch[2];

            // Find the tab content div
            const tabContentRegex = new RegExp(
                `<div\\s+class="tab-content\\s+quality"[^>]*?id="${tabId}"[^>]*>(.*?)</div>\\s*</div>`,
                's'
            );
            const tabContentMatch = html.match(tabContentRegex);
            if (!tabContentMatch) continue;

            const tabHtml = tabContentMatch[1];

            // Extract watch URL
            const watchMatch = tabHtml.match(
                /<a\s+href="(https?:\/\/[^"]+\/watch\/\d+\/[^"]+)"[^>]*class="[^"]*link-show[^"]*"/
            );
            const watchUrl = watchMatch ? watchMatch[1] : null;

            // Extract download URL and size
            const dlMatch = tabHtml.match(
                /<a\s+href="(https?:\/\/[^"]+\/download\/\d+\/[^"]+)"[^>]*class="[^"]*link-download[^"]*">[\s\S]*?<span\s+class="font-size-14\s+mr-auto">([^<]+)<\/span>/
            );
            const dlUrl = dlMatch ? dlMatch[1] : null;
            const size = dlMatch ? dlMatch[2].trim() : 'Unknown';

            const link_id = watchUrl || dlUrl || '';

            qualities.push({
                quality: qualityLabel,
                link_id: link_id,
                watch_url: watchUrl || '',
                download_url: dlUrl || '',
                size: size,
            });
        }

        // Fallback for old-style /link/ pages (if no tabs found)
        if (qualities.length === 0) {
            const singleLine = html.replace(/\n/g, '');
            const linkPattern = /href="https?:\/\/([^"]+\/link\/\d+)"/g;
            const linkMatches = [...singleLine.matchAll(linkPattern)];
            const uniqueLinks = [...new Set(linkMatches.map(m => m[1]))];

            if (uniqueLinks.length > 0) {
                const sizePattern = /font-size-14 mr-auto">([0-9.MGB ]+)<\//g;
                const sizeMatches = [...singleLine.matchAll(sizePattern)];
                const qLabels = ['1080p', '720p', '480p', '360p', '240p'];
                let idx = 0;
                for (const q of qLabels) {
                    if (html.includes(`>${q}</`) && idx < uniqueLinks.length) {
                        const sz = idx < sizeMatches.length ? sizeMatches[idx][1] : 'Unknown';
                        qualities.push({
                            quality: q,
                            link_id: uniqueLinks[idx],
                            watch_url: '',
                            download_url: '',
                            size: sz,
                        });
                        idx++;
                    }
                }
                if (qualities.length === 0) {
                    uniqueLinks.forEach((link, i) => {
                        qualities.push({
                            quality: '720p',
                            link_id: link,
                            watch_url: '',
                            download_url: '',
                            size: i < sizeMatches.length ? sizeMatches[i][1] : 'Unknown',
                        });
                    });
                }
            }
        }

        return qualities;
    }

    // ── Resolve Direct URL ────────────────────────────────────
    // Fetches a watch/download page and extracts the direct MP4 URL.
    async function resolveDirectUrl(targetUrl) {
        if (!targetUrl) return null;
        if (!targetUrl.startsWith('http')) targetUrl = 'https://' + targetUrl;

        try {
            const html = await corsFetch(targetUrl);

            // <source src="...mp4" ...>
            const srcMatch = html.match(/<source\s+src=["']([^"']+\.mp4)["']/);
            if (srcMatch) return srcMatch[1];

            // <a href="...mp4" download>
            const hrefMatch = html.match(/href=["']([^"']+\.mp4)["'][^>]*download/);
            if (hrefMatch) return hrefMatch[1];

            // Any .mp4 href
            const anyMp4 = html.match(/href=["']([^"']+\.mp4)["']/);
            if (anyMp4) return anyMp4[1];

            // Any .mkv href
            const anyMkv = html.match(/href=["']([^"']+\.mkv)["']/);
            if (anyMkv) return anyMkv[1];

            return null;
        } catch {
            return null;
        }
    }

    // ── Resolve Stream URL ────────────────────────────────────
    async function resolveStream(targetUrl) {
        const directUrl = await resolveDirectUrl(targetUrl);
        if (directUrl) {
            return { url: directUrl, referer: targetUrl };
        }
        return { url: null, referer: null };
    }

    // ── Get Download Links ────────────────────────────────────
    async function getDownloadLinks(contentUrl) {
        const qualities = await getQualities(contentUrl);
        return qualities
            .map(q => q.download_url)
            .filter(url => url !== '');
    }

    // ── Bulk Resolve ──────────────────────────────────────────
    async function bulkResolve(episodes) {
        const allQualities = await Promise.all(
            episodes.map(ep => getQualities(ep.url).catch(() => []))
        );
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
                    dlLinksPromise: getDownloadLinks(episodes[i].url).catch(() => []),
                });
            }
        }
        const resolvedUrls = await Promise.all(tasks.map(t => t.resolvePromise));
        const allDlLinks = await Promise.all(tasks.map(t => t.dlLinksPromise));
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

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    return {
        search,
        getEpisodes,
        getQualities,
        resolveDirectUrl,
        resolveStream,
        getDownloadLinks,
        bulkResolve,
        resolveBaseUrl,
        corsFetch,
    };
})();
