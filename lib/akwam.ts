import * as cheerio from 'cheerio';

const HTTP = 'https://';
const RGX_SHORTEN_URL = /https?:\/\/(\w*\.*\w+\.\w+\/download\/.*?)"/;
const RGX_DIRECT_URL = /([a-z0-9]{4,}\.\w+\.\w+\/download\/.*?)"/;
const RGX_DL_URL = /https?:\/\/(\w*\.*\w+\.\w+\/link\/\d+)/g;

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
        const res = await fetch('https://ak.sv/', { redirect: 'follow' });
        this.baseUrl = res.url.replace(/\/$/, '');
    }

    async search(query: string, type: 'movie' | 'series' = 'movie'): Promise<AkwamResult[]> {
        await this.initialize();
        const searchUrl = `${this.baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}&page=1`;
        const res = await fetch(searchUrl);
        const html = await res.text();
        const $ = cheerio.load(html);

        const results: AkwamResult[] = [];
        const pattern = new RegExp(`${this.baseUrl}/${type}/\\d+/.*?`, 'g');

        // The original script used regex on the whole page content.
        // Let's find specific containers if possible, or stick to regex for consistency.
        const matches = html.matchAll(new RegExp(`(${this.baseUrl}/${type}/\\d+/.*?)"`, 'g'));
        const uniqueUrls = new Set<string>();

        for (const match of matches) {
            const url = match[1];
            if (!uniqueUrls.has(url)) {
                uniqueUrls.add(url);
                const name = url.split('/').pop()?.replace(/-/g, ' ') || 'Unknown';
                results.push({
                    name: name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
                    url
                });
            }
        }

        return results.reverse(); // Original script did [::-1]
    }

    async fetchEpisodes(seriesUrl: string): Promise<AkwamResult[]> {
        await this.initialize();
        const res = await fetch(seriesUrl);
        const html = await res.text();
        const matches = html.matchAll(new RegExp(`(${this.baseUrl}/episode/\\d+/.*?)"`, 'g'));
        const results: AkwamResult[] = [];
        const uniqueUrls = new Set<string>();

        for (const match of matches) {
            const url = match[1];
            if (!uniqueUrls.has(url)) {
                uniqueUrls.add(url);
                const name = url.split('/').pop()?.replace(/-/g, ' ') || 'Unknown';
                results.push({
                    name: name.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
                    url
                });
            }
        }
        return results.reverse();
    }

    async getQualities(itemUrl: string): Promise<AkwamQuality[]> {
        await this.initialize();
        const res = await fetch(itemUrl);
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
        let res = await fetch(linkUrl);
        let html = await res.text();
        let shortened = html.match(RGX_SHORTEN_URL);
        if (!shortened) return null;

        let sUrl = shortened[0].replace(/"$/, '');
        if (!sUrl.startsWith('http')) sUrl = 'https://' + sUrl;

        // Step 2: Direct download page
        res = await fetch(sUrl, { redirect: 'follow' });
        if (res.url !== sUrl) {
            res = await fetch(res.url);
        }
        html = await res.text();
        let direct = html.match(RGX_DIRECT_URL);
        if (!direct) return null;

        return 'https://' + direct[1];
    }
}

export const akwamApi = new AkwamAPI();
