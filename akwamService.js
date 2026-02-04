const axios = require('axios');
const cheerio = require('cheerio');
const { CookieJar } = require('tough-cookie');
const { HttpProxyAgent } = require('http-proxy-agent');
const { HttpsProxyAgent } = require('https-proxy-agent');

// Create a persistent cookie jar
const jar = new CookieJar();

/**
 * ProxyManager handles fetching and rotating proxies
 */
class ProxyManager {
    constructor() {
        this.proxies = [];
        this.currentIndex = 0;
        this.customProxy = process.env.PROXY_URL || null;
        this.lastFetch = 0;
    }

    async getProxy() {
        if (this.customProxy) {
            console.log(`[ProxyManager] Using custom proxy: ${this.customProxy}`);
            return this.customProxy;
        }

        // Fetch free proxies from ProxyScrape if list is empty or old (1 hour)
        if (this.proxies.length === 0 || (Date.now() - this.lastFetch > 3600000)) {
            try {
                console.log('[ProxyManager] Fetching fresh proxy list...');
                const response = await axios.get('https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all');
                this.proxies = response.data.trim().split('\r\n').filter(p => p.includes(':'));
                this.lastFetch = Date.now();
                console.log(`[ProxyManager] Fetched ${this.proxies.length} proxies.`);
            } catch (error) {
                console.warn(`[ProxyManager] Failed to fetch proxy list: ${error.message}`);
                return null;
            }
        }

        if (this.proxies.length === 0) return null;

        const proxy = this.proxies[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.proxies.length;
        return `http://${proxy}`;
    }

    getAgent(proxyUrl) {
        if (!proxyUrl) return {};
        const isHttps = proxyUrl.startsWith('https');
        return isHttps
            ? { httpsAgent: new HttpsProxyAgent(proxyUrl) }
            : { httpAgent: new HttpProxyAgent(proxyUrl), httpsAgent: new HttpsProxyAgent(proxyUrl) };
    }
}

const proxyManager = new ProxyManager();

class AkwamService {
    constructor() {
        this.baseUrl = null;
        this.HTTP = 'https://';
        this.isInitialized = false;
        this.currentProxy = null;
    }

    /**
     * Internal request wrapper with manual cookie handling, proxy support, and retry logic
     */
    async request(url, options = {}, retries = 2) {
        try {
            const config = {
                ...options,
                headers: { ...options.headers }
            };

            // 1. Manually add cookies from the jar
            const cookieString = await jar.getCookieString(url);
            if (cookieString) {
                config.headers['Cookie'] = cookieString;
            }

            // 2. Apply proxy agents
            if (this.currentProxy) {
                const agents = proxyManager.getAgent(this.currentProxy);
                Object.assign(config, agents);
            }

            // Standard headers
            config.headers['User-Agent'] = config.headers['User-Agent'] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36';
            config.headers['Accept'] = config.headers['Accept'] || 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7';
            config.headers['Accept-Language'] = config.headers['Accept-Language'] || 'en-US,en;q=0.9,ar;q=0.8';
            config.headers['Connection'] = 'keep-alive';
            config.timeout = 30000;
            config.maxRedirects = 15;

            const response = await axios.get(url, config);

            // 3. Manually store received cookies in the jar
            const setCookie = response.headers['set-cookie'];
            if (setCookie) {
                for (const cookie of setCookie) {
                    await jar.setCookie(cookie, url);
                }
            }

            return response;
        } catch (error) {
            const is403 = error.response && error.response.status === 403;

            if ((is403 || error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT' || error.code === 'ENOTFOUND') && retries > 0) {
                console.log(`[AkwamService] Request failed (${error.message}). Retrying with new proxy...`);
                this.currentProxy = await proxyManager.getProxy();
                return this.request(url, options, retries - 1);
            }
            throw error;
        }
    }

    async init() {
        if (!this.isInitialized) {
            try {
                console.log('[AkwamService] Initializing session...');
                const initialRes = await this.request('https://ak.sv/', {
                    headers: { 'Sec-Fetch-Site': 'none' }
                });

                this.baseUrl = initialRes.request.res.responseUrl.replace(/\/$/, '');
                console.log(`[AkwamService] Resolved base URL: ${this.baseUrl}`);
                this.isInitialized = true;
            } catch (error) {
                console.warn(`[AkwamService] Initialization warning: ${error.message}. Attempting with proxy...`);
                this.currentProxy = await proxyManager.getProxy();
                this.baseUrl = 'https://ak.sv';
                this.isInitialized = true;
            }
        }
        return this.baseUrl;
    }

    async search(query, type = 'movie', page = 1) {
        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}&page=${page}`;
        console.log(`[AkwamService] Searching: ${searchUrl}`);

        try {
            const { data } = await this.request(searchUrl, {
                headers: {
                    'Referer': `${baseUrl}/`,
                    'Sec-Fetch-Site': 'same-origin'
                }
            });

            const domainPattern = baseUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/sv$/, '\\w+');
            const regex = new RegExp(`(${domainPattern}/${type}/\\d+/[^"]+)"`, 'g');
            const matches = [...data.matchAll(regex)];

            const resultsMap = {};
            matches.forEach(match => {
                const url = match[1];
                const slug = url.split('/').pop();
                const title = decodeURIComponent(slug).replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                if (!resultsMap[url]) {
                    resultsMap[url] = title;
                }
            });

            const results = Object.entries(resultsMap).map(([url, title]) => ({ title, url })).reverse();

            return {
                query,
                type,
                page,
                count: results.length,
                results
            };
        } catch (error) {
            console.error(`[AkwamService] Search error: ${error.message}`);
            if (error.response && error.response.status === 403) {
                throw new Error('Access Forbidden (403). Cloudflare is blocking Vercel. Please set a PROXY_URL in your environment variables.');
            }
            throw error;
        }
    }

    async getEpisodes(seriesUrl) {
        const baseUrl = await this.init();
        const safeUrl = new URL(seriesUrl).toString();
        console.log(`[AkwamService] Fetching episodes: ${safeUrl}`);

        try {
            const { data, request } = await this.request(safeUrl, {
                headers: {
                    'Referer': `${baseUrl}/search`,
                    'Sec-Fetch-Site': 'same-origin'
                }
            });
            const finalBaseUrl = request.res.responseUrl.split('/').slice(0, 3).join('/');

            const domainPattern = finalBaseUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`(${domainPattern}/episode/\\d+/[^"]+)"`, 'g');
            const matches = [...data.matchAll(regex)];

            const resultsMap = {};
            matches.forEach(match => {
                const url = match[1];
                const slug = url.split('/').pop();
                const title = decodeURIComponent(slug).replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                if (!resultsMap[url]) {
                    resultsMap[url] = title;
                }
            });

            const episodes = Object.entries(resultsMap).map(([url, title]) => ({ title, url })).reverse();

            return {
                seriesUrl: safeUrl,
                count: episodes.length,
                episodes
            };
        } catch (error) {
            console.error(`[AkwamService] Episodes error: ${error.message}`);
            throw error;
        }
    }

    async getQualities(itemUrl) {
        const baseUrl = await this.init();
        console.log(`[AkwamService] Fetching qualities: ${itemUrl}`);

        try {
            const { data } = await this.request(itemUrl, {
                headers: {
                    'Referer': baseUrl,
                    'Sec-Fetch-Site': 'same-origin'
                }
            });

            const RGX_QUALITY_TAG = /tab-content quality.*?a href="(https?:\/\/[\w.*]+\.[\w]+\/link\/\d+)"/g;
            const RGX_SIZE_TAG = /font-size-14 mr-auto">([0-9.MGB ]+)<\//g;

            const cleanData = data.replace(/\n/g, '');
            const qualityLinks = [...cleanData.matchAll(RGX_QUALITY_TAG)];
            const sizes = [...cleanData.matchAll(RGX_SIZE_TAG)];

            const qualities = [];
            const qualityNames = ['1080p', '720p', '480p'];
            let i = 0;

            qualityNames.forEach(q => {
                if (cleanData.includes(`>${q}</`)) {
                    qualities.push({
                        quality: q,
                        link: qualityLinks[i] ? qualityLinks[i][1] : null,
                        size: sizes[i] ? sizes[i][1].trim() : null
                    });
                    i++;
                }
            });

            return {
                itemUrl,
                count: qualities.length,
                qualities
            };
        } catch (error) {
            console.error(`[AkwamService] Qualities error: ${error.message}`);
            throw error;
        }
    }

    async getDirectUrl(qualityLink) {
        console.log(`[AkwamService] Resolving direct URL: ${qualityLink}`);

        try {
            const res1 = await this.request(qualityLink, {
                headers: { 'Sec-Fetch-Site': 'cross-site' }
            });

            const shortenMatch = res1.data.match(/https?:\/\/([\w.*]+\.[\w]+\/download\/[^"]+)"/);

            if (!shortenMatch) {
                return {
                    success: false,
                    error: 'Could not find download link on page',
                    fallbackUrl: qualityLink
                };
            }

            const shortenUrl = this.HTTP + shortenMatch[1];
            console.log(`[AkwamService] Found shorten URL: ${shortenUrl}`);

            const res2 = await this.request(shortenUrl);
            let finalPage = res2.data;
            let finalUrl = res2.request.res.responseUrl;

            const directMatch = finalPage.match(/([a-z0-9]{4,}\.[\w]+\.[\w]+\/download\/[^"]+)"/);

            if (directMatch) {
                return {
                    success: true,
                    directUrl: this.HTTP + directMatch[1]
                };
            }

            return {
                success: false,
                error: 'Could not extract direct URL (server link expired or protection active)',
                fallbackUrl: shortenUrl
            };

        } catch (error) {
            console.error(`[AkwamService] Direct link error: ${error.message}`);
            return {
                success: false,
                error: error.message,
                fallbackUrl: qualityLink
            };
        }
    }

    async getAllEpisodeLinks(seriesUrl, quality = '720p') {
        const { episodes } = await this.getEpisodes(seriesUrl);
        const results = [];

        for (const episode of episodes) {
            try {
                const { qualities } = await this.getQualities(episode.url);
                let qualityInfo = qualities.find(q => q.quality === quality) || qualities[0];

                if (qualityInfo && qualityInfo.link) {
                    const directResult = await this.getDirectUrl(qualityInfo.link);
                    results.push({
                        ...episode,
                        quality: qualityInfo.quality,
                        size: qualityInfo.size,
                        ...directResult
                    });
                }
            } catch (error) {
                results.push({
                    ...episode,
                    success: false,
                    error: error.message
                });
            }
        }

        return {
            seriesUrl,
            quality,
            count: results.length,
            episodes: results
        };
    }
}

module.exports = new AkwamService();
