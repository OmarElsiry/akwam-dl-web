const axios = require('axios');
const cheerio = require('cheerio');

class AkwamService {
    constructor() {
        this.baseUrl = null;
        this.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://ak.sv/',
            'Origin': 'https://ak.sv',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        };
    }

    async init() {
        if (!this.baseUrl) {
            try {
                const response = await axios.get('https://ak.sv/', {
                    maxRedirects: 5,
                    validateStatus: null,
                    headers: this.headers
                });
                this.baseUrl = response.request.res.responseUrl.replace(/\/$/, '');
            } catch (err) {
                this.baseUrl = 'https://ak.sv';
            }
        }
        return this.baseUrl;
    }

    async search(query, type = 'movie') {
        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}`;

        try {
            const { data } = await axios.get(searchUrl, {
                headers: { ...this.headers, 'Referer': `${baseUrl}/` }
            });
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
        } catch (err) {
            if (err.response?.status === 403) throw new Error('Cloudflare Blocked Vercel IP. Try running locally or use a Proxy.');
            throw err;
        }
    }

    async getEpisodes(seriesUrl) {
        const { data } = await axios.get(seriesUrl, { headers: this.headers });
        const $ = cheerio.load(data);
        const episodes = [];
        const baseUrl = await this.init();
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
        const { data } = await axios.get(itemUrl, { headers: this.headers });
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
        const res1 = await axios.get(linkUrl, { headers: this.headers });
        const $1 = cheerio.load(res1.data);
        let shortenUrl = '';
        $1('a').each((i, el) => {
            const href = $1(el).attr('href');
            if (href && href.includes('/download/')) shortenUrl = href;
        });
        if (!shortenUrl) throw new Error('Download gate blocked resolution.');
        const res2 = await axios.get(shortenUrl, { headers: this.headers });
        const match = res2.data.match(/window\.location\.href\s*=\s*"(.*?)"/);
        return match ? match[1] : shortenUrl;
    }
}

module.exports = new AkwamService();
