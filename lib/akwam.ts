import * as cheerio from 'cheerio';

const HTTP = 'https://';
const RGX_SHORTEN_URL = /https?:\/\/(\w*\.*\w+\.\w+\/download\/.*?)"/;
const RGX_DIRECT_URL = /([a-z0-9]{4,}\.\w+\.\w+\/download\/.*?)"/;
const RGX_DL_URL = /https?:\/\/(\w*\.*\w+\.\w+\/link\/\d+)/g;

const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
};

export interface AkwamResult {
    name: string;
    url: string;
}

export interface AkwamQuality {
    quality: string;
    link: string;
}

export class AkwamAPI {
    private baseUrl: string = '';

    private async initialize() {
        if (this.baseUrl) return;
        const res = await fetch('https://ak.sv/', {
            redirect: 'follow',
            headers: HEADERS
        });
        // Use origin to avoid subpaths like /main
        const urlObj = new URL(res.url);
        this.baseUrl = urlObj.origin;
        console.log(`[DEBUG] Initialized Base URL: ${this.baseUrl}`);
    }

    async search(query: string, type: 'movie' | 'series' = 'movie'): Promise<AkwamResult[]> {
        await this.initialize();
        const formattedQuery = query.trim().replace(/\s+/g, '+');
        const searchUrl = `${this.baseUrl}/search?q=${formattedQuery}&section=${type}&page=1`;

        const res = await fetch(searchUrl, {
            headers: {
                ...HEADERS,
                'Referer': this.baseUrl + '/',
            }
        });
        const html = await res.text();
        const $ = cheerio.load(html);

        const results: AkwamResult[] = [];
        const uniqueUrls = new Set<string>();

        // Find all links matching the pattern
        $(`a[href*="/${type}/"]`).each((_, el) => {
            let url = $(el).attr('href');
            if (!url) return;

            // Handle relative URLs
            if (url.startsWith('/')) {
                url = this.baseUrl + url;
            }

            // Verify it's a valid result URL (e.g., contains /movie/ID/slug)
            const pattern = new RegExp(`/${type}/\\d+/`);
            if (pattern.test(url) && !uniqueUrls.has(url)) {
                uniqueUrls.add(url);
                const name = url.split('/').pop()?.replace(/-/g, ' ') || 'Unknown';
                results.push({
                    name: name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
                    url
                });
            }
        });

        // If Cheerio missed it (rare), fall back to regex
        if (results.length === 0) {
            const escapeRegex = (string: string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const baseUrlPattern = escapeRegex(this.baseUrl);
            const regex = new RegExp(`(?:${baseUrlPattern})?(/${type}/\\d+/.*?)"`, 'g');
            const matches = html.matchAll(regex);
            for (const match of matches) {
                let url = match[1];
                if (!url.startsWith('http')) url = this.baseUrl + url;
                if (!uniqueUrls.has(url)) {
                    uniqueUrls.add(url);
                    const name = url.split('/').pop()?.replace(/-/g, ' ') || 'Unknown';
                    results.push({
                        name: name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
                        url
                    });
                }
            }
        }

        return results.reverse();
    }

    async fetchEpisodes(seriesUrl: string): Promise<AkwamResult[]> {
        await this.initialize();
        const res = await fetch(seriesUrl, { headers: HEADERS });
        const html = await res.text();
        const $ = cheerio.load(html);
        const results: AkwamResult[] = [];
        const uniqueUrls = new Set<string>();

        $(`a[href*="/episode/"]`).each((_, el) => {
            let url = $(el).attr('href');
            if (!url) return;
            if (url.startsWith('/')) url = this.baseUrl + url;

            const pattern = /\/episode\/\d+\//;
            if (pattern.test(url) && !uniqueUrls.has(url)) {
                uniqueUrls.add(url);
                const name = url.split('/').pop()?.replace(/-/g, ' ') || 'Unknown';
                results.push({
                    name: name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
                    url
                });
            }
        });

        return results;
    }

    async getQualities(itemUrl: string): Promise<AkwamQuality[]> {
        await this.initialize();
        const res = await fetch(itemUrl, { headers: HEADERS });
        const html = await res.text();
        const $ = cheerio.load(html);

        const qualities: AkwamQuality[] = [];
        const links = html.match(RGX_DL_URL) || [];

        let i = 0;
        for (const q of ['1080p', '720p', '480p']) {
            if (html.includes(`>${q}</`)) {
                if (i < links.length) {
                    qualities.push({ quality: q, link: links[i] });
                    i++;
                }
            }
        }
        return qualities;
    }

    async getDirectUrl(linkUrl: string): Promise<string | null> {
        if (!linkUrl.startsWith('http')) linkUrl = 'https://' + linkUrl;

        // Step 1: Shortened downloader page
        let res = await fetch(linkUrl, { headers: HEADERS });
        let html = await res.text();
        let shortened = html.match(RGX_SHORTEN_URL);
        if (!shortened) return null;

        let sUrl = shortened[0].replace(/"$/, '');
        if (!sUrl.startsWith('http')) sUrl = 'https://' + sUrl;

        // Step 2: Direct download page
        res = await fetch(sUrl, {
            redirect: 'follow',
            headers: HEADERS
        });
        if (res.url !== sUrl) {
            res = await fetch(res.url, { headers: HEADERS });
        }
        html = await res.text();
        let direct = html.match(RGX_DIRECT_URL);
        if (!direct) return null;

        return 'https://' + direct[1];
    }
}

export const akwamApi = new AkwamAPI();
