const axios = require('axios');
const cheerio = require('cheerio');

class AkwamService {
    constructor() {
        this.baseUrl = 'https://ak.sv';
        this.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Referer': 'https://ak.sv/',
        };

        // List of ways to get the data
        this.proxyTemplates = [
            (url) => url, // Direct
            (url) => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
            (url) => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`
        ];
    }

    /**
     * The "Proxy Race": Fire all requests at once. The first one 
     * that returns valid (non-blocked) content wins.
     */
    async fetchWithProxy(url) {
        const fetchers = this.proxyTemplates.map(async (proxyFn) => {
            const finalUrl = proxyFn(url);
            try {
                const response = await axios.get(finalUrl, {
                    headers: this.headers,
                    timeout: 6000 // Short timeout to fail fast
                });

                const data = response.data;
                const content = typeof data === 'string' ? data : JSON.stringify(data);

                // Validate that we didn't just get a Cloudflare block page
                if (content.includes('Just a moment...') || content.includes('cloudflare-static')) {
                    throw new Error('Blocked by Cloudflare');
                }

                return content;
            } catch (err) {
                // Silently fail so other promises can continue
                throw err;
            }
        });

        // Promise.any takes the first one that successfully RESOLVES
        try {
            return await Promise.any(fetchers);
        } catch (err) {
            throw new Error('All proxies are blocked or too slow. Cloudflare won this round.');
        }
    }

    async search(query, type = 'movie') {
        const searchUrl = `${this.baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}`;
        const data = await this.fetchWithProxy(searchUrl);
        const $ = cheerio.load(data);
        const results = [];

        // Dynamic search for items
        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && href.includes(`/${type}/`)) {
                const item = $(el).closest('.col-12, .col-6, .col-4, .col-3, .item');
                let title = item.find('h3, h2, .entry-title').text().trim() || $(el).text().trim();
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
                const title = $(el).text().trim();
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
        // Step 1: Intermediate Page
        const data1 = await this.fetchWithProxy(linkUrl);
        const $1 = cheerio.load(data1);
        let shortenUrl = '';

        $1('a').each((i, el) => {
            const href = $1(el).attr('href');
            if (href && href.includes('/download/')) shortenUrl = href;
        });

        if (!shortenUrl) throw new Error('Download gate blocked resolution.');

        // Step 2: Final Page
        const data2 = await this.fetchWithProxy(shortenUrl);

        // Strategy A: JavaScript Redirection
        const match = data2.match(/window\.location\.href\s*=\s*"(.*?)"/);
        if (match) return match[1];

        // Strategy B: Fallback to the Short URL if it's actually the direct file
        // Sometimes Akwam changes behavior so the /download/ link IS the direct link
        return shortenUrl;
    }
}

module.exports = new AkwamService();
