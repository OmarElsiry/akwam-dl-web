const axios = require('axios');
const cheerio = require('cheerio');

class AkwamService {
    constructor() {
        this.baseUrl = null;
        this.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Referer': 'https://ak.sv/',
            'Origin': 'https://ak.sv'
        };

        // --- PROXY LIST ---
        // We use functions to generate the proxy URL dynamically
        this.proxies = [
            // AllOrigins: robust, usually handles basic requests well
            (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
            // CodeTabs: another specialized CORS proxy
            (url) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`,
            // Direct: Try direct as a backup (works on localhost)
            (url) => url
        ];

        // --- CACHE ---
        this.cache = new Map();
        this.CACHE_TTL = 60 * 60 * 1000; // 1 Hour
    }

    // --- CACHE HELPERS ---
    _getFromCache(key) {
        if (this.cache.has(key)) {
            const entry = this.cache.get(key);
            if (Date.now() - entry.timestamp < this.CACHE_TTL) {
                console.log(`[CACHE HIT] ${key}`);
                return entry.val;
            }
            this.cache.delete(key);
        }
        return null;
    }

    _setCache(key, val) {
        if (val && (Array.isArray(val) ? val.length > 0 : true)) {
            this.cache.set(key, { val, timestamp: Date.now() });
        }
    }

    async init() {
        if (!this.baseUrl) {
            this.baseUrl = 'https://ak.sv';
        }
        return this.baseUrl;
    }

    // --- FETCHING ENGINE ---
    async fetchWithProxy(targetUrl) {
        console.log(`Fetching: ${targetUrl}`);

        // 1. Define the fetching logic for a single proxy
        const trySingleProxy = async (proxyFn, index) => {
            const finalUrl = proxyFn(targetUrl);
            try {
                const response = await axios.get(finalUrl, {
                    headers: this.headers,
                    timeout: 8000 // 8s timeout per proxy
                });

                // Cloudflare Check
                if (typeof response.data === 'string' && response.data.includes('Just a moment...')) {
                    throw new Error('Cloudflare Block');
                }
                return response.data;
            } catch (err) {
                throw new Error(`Proxy ${index} failed`);
            }
        };

        // 2. Race them all! (Parallel Execution)
        // We use Promise.any to take the FIRST successful response
        try {
            const proxyPromises = this.proxies.map((fn, idx) => trySingleProxy(fn, idx));
            return await Promise.any(proxyPromises);
        } catch (aggregateError) {
            console.error('All proxies failed:', aggregateError.errors);
            throw new Error('Unable to fetch content. Akwam is blocking all access paths.');
        }
    }

    // --- API METHODS ---

    async search(query, type = 'movie') {
        const cacheKey = `search_${query}_${type}`;
        const cached = this._getFromCache(cacheKey);
        if (cached) return cached;

        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}`;

        const data = await this.fetchWithProxy(searchUrl);
        const $ = cheerio.load(data);
        const results = [];
        const regex = new RegExp([baseUrl, type, '\\d+', '.*?'].join('/'));

        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && (regex.test(href) || href.includes(`/${type}/`))) {
                const item = $(el).closest('.col-12, .col-6, .col-4, .col-3, .item');
                let title = item.find('h3, h2, .entry-title').text().trim() || $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');

                // Clean title
                title = title.replace(/\s+/g, ' ').trim();

                if (!results.find(r => r.url === href) && title.length > 2) {
                    results.push({ title, url: href });
                }
            }
        });

        this._setCache(cacheKey, results);
        return results;
    }

    async getEpisodes(seriesUrl) {
        const cacheKey = `episodes_${seriesUrl}`;
        const cached = this._getFromCache(cacheKey);
        if (cached) return cached;

        const data = await this.fetchWithProxy(seriesUrl);
        const $ = cheerio.load(data);
        const episodes = [];

        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && href.includes('/episode/')) {
                const title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
                if (!episodes.find(e => e.url === href)) {
                    episodes.push({ title, url: href });
                }
            }
        });

        const finalEpisodes = episodes.reverse();
        this._setCache(cacheKey, finalEpisodes);
        return finalEpisodes;
    }

    async getDownloadLinks(itemUrl) {
        // No caching for links as they might expire/rotate
        const data = await this.fetchWithProxy(itemUrl);
        const $ = cheerio.load(data);
        const qualities = [];

        $('.quality-item, .download-item, a[href*="/link/"]').each((i, el) => {
            const href = $(el).attr('href') || $(el).find('a').attr('href');
            if (href && href.includes('/link/')) {
                const qualityText = $(el).text().trim();
                const sizeText = $(el).find('.font-size-14').text().trim();

                qualities.push({
                    quality: qualityText.match(/\d+p/)?.[0] || 'HD',
                    link: href,
                    size: sizeText || 'Unknown'
                });
            }
        });
        return qualities;
    }

    async resolveDirectLink(linkUrl) {
        // No caching for final links
        const data1 = await this.fetchWithProxy(linkUrl);
        const $1 = cheerio.load(data1);
        let shortenUrl = '';
        $1('a').each((i, el) => {
            const href = $1(el).attr('href');
            if (href && href.includes('/download/')) shortenUrl = href;
        });

        if (!shortenUrl) throw new Error('Download gate blocked resolution.');

        const data2 = await this.fetchWithProxy(shortenUrl);
        const match = data2.match(/window\.location\.href\s*=\s*"(.*?)"/);
        return match ? match[1] : shortenUrl;
    }
}

module.exports = new AkwamService();
