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
        // Free proxies to fallback to if Vercel is blocked
        this.proxies = [
            (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
            (url) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`,
            (url) => url // Direct
        ];
    }

    async init() {
        if (!this.baseUrl) {
            this.baseUrl = 'https://ak.sv'; // Default to start
        }
        return this.baseUrl;
    }

    async fetchWithProxy(url) {
        let lastError = null;

        // Try direct first, then proxies
        for (const proxyFn of this.proxies) {
            const finalUrl = proxyFn(url);
            try {
                console.log(`Fetching: ${finalUrl}`);
                const { data } = await axios.get(finalUrl, {
                    headers: this.headers,
                    timeout: 10000
                });

                // If it's the "Just a moment" page, keep trying proxies
                if (typeof data === 'string' && data.includes('Just a moment...')) {
                    console.warn(`Cloudflare detected on ${finalUrl}, trying next...`);
                    continue;
                }

                return data;
            } catch (err) {
                lastError = err;
                console.error(`Fetch failed on ${finalUrl}: ${err.message}`);
            }
        }
        throw lastError || new Error('All fetch attempts failed');
    }

    async search(query, type = 'movie') {
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
                if (!results.find(r => r.url === href) && title.length > 2) {
                    results.push({ title, url: href });
                }
            }
        });
        return results;
    }

    async getEpisodes(seriesUrl) {
        const data = await this.fetchWithProxy(seriesUrl);
        const $ = cheerio.load(data);
        const episodes = [];
        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && href.includes('/episode/')) {
                const title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
                if (!episodes.find(e => e.url === href)) episodes.push({ title, url: href });
            }
        });
        return episodes.reverse();
    }

    async getDownloadLinks(itemUrl) {
        const data = await this.fetchWithProxy(itemUrl);
        const $ = cheerio.load(data);
        const qualities = [];
        $('.quality-item, .download-item, a[href*="/link/"]').each((i, el) => {
            const href = $(el).attr('href') || $(el).find('a').attr('href');
            if (href && href.includes('/link/')) {
                qualities.push({
                    quality: $(el).text().trim().match(/\d+p/)?.[0] || 'HD',
                    link: href,
                    size: $(el).find('.font-size-14').text().trim()
                });
            }
        });
        return qualities;
    }

    async resolveDirectLink(linkUrl) {
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
