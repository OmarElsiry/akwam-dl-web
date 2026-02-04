const axios = require('axios');
const cheerio = require('cheerio');

class AkwamService {
    constructor() {
        this.baseUrl = null;
        this.HTTP = 'https://';
    }

    async init() {
        if (!this.baseUrl) {
            try {
                const response = await axios.get('https://ak.sv/', {
                    maxRedirects: 5,
                    timeout: 10000
                });
                this.baseUrl = response.request.res.responseUrl.replace(/\/$/, '');
                console.log(`[AkwamService] Resolved base URL: ${this.baseUrl}`);
            } catch (error) {
                this.baseUrl = 'https://ak.sv';
                console.log(`[AkwamService] Using fallback URL: ${this.baseUrl}`);
            }
        }
        return this.baseUrl;
    }

    async search(query, type = 'movie', page = 1) {
        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}&page=${page}`;
        console.log(`[AkwamService] Searching: ${searchUrl}`);

        const { data } = await axios.get(searchUrl, { timeout: 10000 });

        // Python regex: ({self.url}/{self.type}/\d+/.*?)"
        const regex = new RegExp(`(${baseUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/${type}/\\d+/[^"]+)"`, 'g');
        const matches = [...data.matchAll(regex)];

        const resultsMap = {};
        matches.forEach(match => {
            const url = match[1];
            const slug = url.split('/').pop();
            const title = slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            if (!resultsMap[url]) {
                resultsMap[url] = title;
            }
        });

        // Convert to array and reverse (Python does [::-1])
        const results = Object.entries(resultsMap).map(([url, title]) => ({ title, url })).reverse();

        return {
            query,
            type,
            page,
            count: results.length,
            results
        };
    }

    async getEpisodes(seriesUrl) {
        const baseUrl = await this.init();
        console.log(`[AkwamService] Fetching episodes: ${seriesUrl}`);

        const { data } = await axios.get(seriesUrl, { timeout: 10000 });

        // Python regex: ({self.url}/episode/\d+/.*?)"
        const regex = new RegExp(`(${baseUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/episode/\\d+/[^"]+)"`, 'g');
        const matches = [...data.matchAll(regex)];

        const resultsMap = {};
        matches.forEach(match => {
            const url = match[1];
            const slug = url.split('/').pop();
            const title = slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            if (!resultsMap[url]) {
                resultsMap[url] = title;
            }
        });

        const episodes = Object.entries(resultsMap).map(([url, title]) => ({ title, url })).reverse();

        return {
            seriesUrl,
            count: episodes.length,
            episodes
        };
    }

    async getQualities(itemUrl) {
        const baseUrl = await this.init();
        console.log(`[AkwamService] Fetching qualities: ${itemUrl}`);

        const { data } = await axios.get(itemUrl, { timeout: 10000 });

        // Python regexes
        const RGX_QUALITY_TAG = /tab-content quality.*?a href="(https?:\/\/[\w.*]+\.[\w]+\/link\/\d+)"/g;
        const RGX_SIZE_TAG = /font-size-14 mr-auto">([0-9.MGB ]+)<\//g;

        // Remove newlines for matching (Python does no_multi_line=True)
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
    }

    async getDirectUrl(qualityLink) {
        console.log(`[AkwamService] Resolving direct URL: ${qualityLink}`);

        try {
            // Step 1: Get the shortened URL page
            const res1 = await axios.get(qualityLink, { timeout: 15000 });

            // Python regex: RGX_SHORTEN_URL = r'https?://(\w*\.*\w+\.\w+/download/.*?)"'
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

            // Step 2: Follow the shortened URL
            const res2 = await axios.get(shortenUrl, { timeout: 15000 });
            let finalPage = res2.data;
            let finalUrl = res2.request.res.responseUrl;

            // If redirected, follow it
            if (shortenUrl !== finalUrl) {
                console.log(`[AkwamService] Redirected to: ${finalUrl}`);
                const res3 = await axios.get(finalUrl, { timeout: 15000 });
                finalPage = res3.data;
            }

            // Python regex: RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
            const directMatch = finalPage.match(/([a-z0-9]{4,}\.[\w]+\.[\w]+\/download\/[^"]+)"/);

            if (directMatch) {
                return {
                    success: true,
                    directUrl: this.HTTP + directMatch[1]
                };
            }

            return {
                success: false,
                error: 'Could not extract direct URL (server may be blocking)',
                fallbackUrl: shortenUrl
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                fallbackUrl: qualityLink
            };
        }
    }

    async getAllEpisodeLinks(seriesUrl, quality = '720p') {
        console.log(`[AkwamService] Getting all episode links for: ${seriesUrl}`);

        const { episodes } = await this.getEpisodes(seriesUrl);
        const results = [];

        for (const episode of episodes) {
            try {
                console.log(`[AkwamService] Processing: ${episode.title}`);
                const { qualities } = await this.getQualities(episode.url);

                // Find requested quality or fallback to first available
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
