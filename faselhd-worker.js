// ============================================================
//  FaselhdWorker — Client-Side FaselHD Helper
//  Delegates to server API; provides direct embed resolution
//  fallback via CORS proxy chain in the browser.
// ============================================================

const FaselhdWorker = (() => {
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
                    signal: AbortSignal.timeout(10000),
                });
                if (!resp.ok) {
                    lastError = new Error(`HTTP ${resp.status} from proxy ${proxiedUrl}`);
                    continue;
                }
                const text = await resp.text();
                if (workingProxyIndex !== idx) {
                    console.log(`[FaselhdWorker] Switched CORS proxy to index ${idx}`);
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

    async function resolveEmbedDirectly(embedUrl) {
        try {
            const html = await corsFetch(embedUrl);
            const srcMatch = html.match(/src=["']([^"']+)["']/i);
            if (srcMatch) return srcMatch[1];
            const fileMatch = html.match(/file["']?\s*:\s*["']([^"']+)["']/i);
            if (fileMatch) return fileMatch[1];
            return null;
        } catch {
            return null;
        }
    }

    return {
        resolveEmbedDirectly,
        corsFetch,
    };
})();
