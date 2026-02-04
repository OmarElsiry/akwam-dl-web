const axios = require('axios');
const cheerio = require('cheerio');
const wrapper = require('axios-cookiejar-support').wrapper;
const { CookieJar } = require('tough-cookie');

// Create a persistent cookie jar
const jar = new CookieJar();

// Create axios instance with cookie support and browser-like headers
const client = wrapper(axios.create({
    jar,
    timeout: 20000,
    maxRedirects: 15,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'DNT': '1'
    }
}));

class AkwamService {
    constructor() {
        this.baseUrl = null;
        this.HTTP = 'https://';
        this.isInitialized = false;
    }

    async init() {
        if (!this.isInitialized) {
            try {
                console.log('[AkwamService] Initializing session...');
                // First visit the core domain to get initial cookies
                const initialRes = await client.get('https://ak.sv/', {
                    headers: { 'Sec-Fetch-Site': 'none' }
                });

                this.baseUrl = initialRes.request.res.responseUrl.replace(/\/$/, '');
                console.log(`[AkwamService] Resolved base URL: ${this.baseUrl}`);
                this.isInitialized = true;
            } catch (error) {
                console.warn(`[AkwamService] Initialization warning: ${error.message}`);
                this.baseUrl = 'https://ak.sv';
                this.isInitialized = true; // Still mark as initialized to avoid loops
            }
        }
        return this.baseUrl;
    }

    async search(query, type = 'movie', page = 1) {
        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}&page=${page}`;
        console.log(`[AkwamService] Searching: ${searchUrl}`);

        try {
            const { data } = await client.get(searchUrl, {
                headers: {
                    'Referer': `${baseUrl}/`,
                    'Sec-Fetch-Site': 'same-origin'
                }
            });

            // Match Python regex: ({self.url}/{self.type}/\d+/.*?)"
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
                throw new Error('Access Forbidden (403). Cloudflare may be blocking this request.');
            }
            throw error;
        }
    }

    async getEpisodes(seriesUrl) {
        const baseUrl = await this.init();
        const safeUrl = new URL(seriesUrl).toString();
        console.log(`[AkwamService] Fetching episodes: ${safeUrl}`);

        try {
            const { data, request } = await client.get(safeUrl, {
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
            const { data } = await client.get(itemUrl, {
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
            const res1 = await client.get(qualityLink, {
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

            const res2 = await client.get(shortenUrl);
            let finalPage = res2.data;
            let finalUrl = res2.request.res.responseUrl;

            if (shortenUrl !== finalUrl) {
                console.log(`[AkwamService] Followed redirect to: ${finalUrl}`);
                const res3 = await client.get(finalUrl);
                finalPage = res3.data;
            }

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
                } else {
                    results.push({
                        ...episode,
                        success: false,
                        error: 'No quality links found'
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
