const axios = require('axios');
const cheerio = require('cheerio');

class AkwamService {
    constructor() {
        this.baseUrl = null;
        // The "Secret Sauce": Impersonating Googlebot often bypasses Cloudflare challenges
        this.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
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
                console.log(`Resolved Akwam Base URL: ${this.baseUrl}`);
            } catch (err) {
                console.error('Init failed, using default');
                this.baseUrl = 'https://ak.sv';
            }
        }
        return this.baseUrl;
    }

    async search(query, type = 'movie') {
        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}`;

        const { data } = await axios.get(searchUrl, { headers: this.headers });
        const $ = cheerio.load(data);
        const results = [];

        const regexArr = [baseUrl, type, '\\d+', '.*?'].join('/');
        const regex = new RegExp(regexArr);

        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && (regex.test(href) || href.includes(`/${type}/`))) {
                const item = $(el).closest('.col-12, .col-6, .col-4, .col-3, .item');
                let title = '';
                if (item.length) {
                    title = item.find('h3, h2, .entry-title').text().trim();
                }
                if (!title) {
                    title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
                }
                if (!results.find(r => r.url === href) && title.length > 2) {
                    results.push({ title, url: href });
                }
            }
        });

        return results;
    }

    async getEpisodes(seriesUrl) {
        const { data } = await axios.get(seriesUrl, { headers: this.headers });
        const $ = cheerio.load(data);
        const episodes = [];
        const baseUrl = await this.init();

        const regexArr = [baseUrl, 'episode', '\\d+', '.*?'].join('/');
        const regex = new RegExp(regexArr);

        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && (regex.test(href) || href.includes('/episode/'))) {
                const title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
                if (!episodes.find(e => e.url === href)) {
                    episodes.push({ title, url: href });
                }
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
            const qualityText = $(el).text().trim();
            const size = $(el).find('.font-size-14').text().trim();

            if (href && href.includes('/link/')) {
                qualities.push({
                    quality: qualityText.match(/\d+p/)?.[0] || 'HD',
                    link: href,
                    size: size
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

        if (!shortenUrl) throw new Error('Could not find intermediate download link');

        const res2 = await axios.get(shortenUrl, { headers: this.headers });
        const $2 = cheerio.load(res2.data);
        let directLink = '';
        $2('a').each((i, el) => {
            const href = $2(el).attr('href');
            if (href && href.includes('/download/') && !href.includes(shortenUrl)) {
                directLink = href;
            }
        });

        if (!directLink) {
            const scriptContent = res2.data;
            const match = scriptContent.match(/window\.location\.href\s*=\s*"(.*?)"/);
            if (match) directLink = match[1];
        }

        return directLink || shortenUrl;
    }
}

module.exports = new AkwamService();
