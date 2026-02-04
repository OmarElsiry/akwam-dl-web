const axios = require('axios');
const cheerio = require('cheerio');

const fs = require('fs');
const path = require('path');

class AkwamService {
    constructor() {
        this.baseUrl = null;
        this.activeDownloads = new Map(); // Track progress
    }

    async init() {
        if (!this.baseUrl) {
            const response = await axios.get('https://ak.sv/', {
                maxRedirects: 5,
                validateStatus: null
            });
            // Akwam often redirects to the current working domain
            this.baseUrl = response.request.res.responseUrl.replace(/\/$/, '');
            console.log(`Resolved Akwam Base URL: ${this.baseUrl}`);
        }
        return this.baseUrl;
    }

    async search(query, type = 'movie') {
        const baseUrl = await this.init();
        const searchUrl = `${baseUrl}/search?q=${encodeURIComponent(query)}&section=${type}`;

        const { data } = await axios.get(searchUrl);
        const $ = cheerio.load(data);
        const results = [];

        // Akwam typically has items in a grid or list.
        // The python script used regex: (base_url/type/id/slug)
        const regexArr = [baseUrl, type, '\\d+', '.*?'].join('/');
        const regex = new RegExp(regexArr);

        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && regex.test(href)) {
                // To get the title, we can look for a nested title class or use text
                const item = $(el).closest('.col-12, .col-6, .col-4, .col-3, .item'); // Common grid classes
                let title = '';

                if (item.length) {
                    title = item.find('h3, h2, .entry-title').text().trim();
                }

                if (!title) {
                    title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
                }

                // Avoid duplicates
                if (!results.find(r => r.url === href)) {
                    results.push({ title, url: href });
                }
            }
        });

        return results;
    }

    async getEpisodes(seriesUrl) {
        const { data } = await axios.get(seriesUrl);
        const $ = cheerio.load(data);
        const episodes = [];
        const baseUrl = await this.init();

        const regexArr = [baseUrl, 'episode', '\\d+', '.*?'].join('/');
        const regex = new RegExp(regexArr);

        $('a').each((i, el) => {
            const href = $(el).attr('href');
            if (href && regex.test(href)) {
                const title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
                if (!episodes.find(e => e.url === href)) {
                    episodes.push({ title, url: href });
                }
            }
        });

        // Sort episodes if they have numbers in title
        return episodes.reverse(); // Akwam usually lists latest first in HTML
    }

    async getDownloadLinks(itemUrl) {
        const { data } = await axios.get(itemUrl);
        const $ = cheerio.load(data);
        const qualities = [];

        // Akwam quality boxes usually have classes like .quality or .download-item
        // The python script looked for 'tab-content quality'
        $('.quality-item, .download-item, a[href*="/link/"]').each((i, el) => {
            const href = $(el).attr('href') || $(el).find('a').attr('href');
            const qualityText = $(el).text().trim();
            const size = $(el).find('.font-size-14').text().trim(); // Based on python regex RGX_SIZE_TAG

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
        // Step 1: Follow the link to the intermediate page
        const res1 = await axios.get(linkUrl);
        const $1 = cheerio.load(res1.data);

        // Find the download button/link which usually has /download/ in it
        let shortenUrl = '';
        $1('a').each((i, el) => {
            const href = $1(el).attr('href');
            if (href && href.includes('/download/')) {
                shortenUrl = href;
            }
        });

        if (!shortenUrl) throw new Error('Could not find intermediate download link');

        // Step 2: Get the direct URL from the shorten URL
        const res2 = await axios.get(shortenUrl);
        const $2 = cheerio.load(res2.data);

        let directLink = '';
        $2('a').each((i, el) => {
            const href = $2(el).attr('href');
            if (href && href.includes('/download/') && !href.includes(shortenUrl)) {
                directLink = href;
            }
        });

        // Fallback: search in script
        if (!directLink) {
            const scriptContent = res2.data;
            const match = scriptContent.match(/window\.location\.href\s*=\s*"(.*?)"/);
            if (match) directLink = match[1];
        }

        return directLink || shortenUrl; // Sometimes shortenUrl IS the direct one after redirect
    }

    async downloadFile(url, fileName) {
        const downloadDir = path.join(process.cwd(), 'downloads');
        if (!fs.existsSync(downloadDir)) {
            fs.mkdirSync(downloadDir);
        }

        const safeName = fileName.replace(/[<>:"/\\|?*]/g, '_');
        const filePath = path.join(downloadDir, safeName + '.mp4');
        const downloadId = Date.now().toString();

        this.activeDownloads.set(downloadId, {
            name: fileName,
            progress: 0,
            status: 'starting'
        });

        // Background task
        this._startDownload(downloadId, url, filePath);

        return downloadId;
    }

    async _startDownload(id, url, filePath) {
        try {
            const { data, headers } = await axios({
                url,
                method: 'GET',
                responseType: 'stream'
            });

            const totalLength = headers['content-length'];
            let downloadedLength = 0;
            const writer = fs.createWriteStream(filePath);

            data.on('data', (chunk) => {
                downloadedLength += chunk.length;
                const progress = Math.round((downloadedLength / totalLength) * 100);
                this.activeDownloads.set(id, {
                    ...this.activeDownloads.get(id),
                    progress,
                    status: 'downloading'
                });
            });

            data.pipe(writer);

            return new Promise((resolve, reject) => {
                writer.on('finish', () => {
                    this.activeDownloads.set(id, {
                        ...this.activeDownloads.get(id),
                        progress: 100,
                        status: 'completed',
                        path: filePath
                    });
                    resolve();
                });
                writer.on('error', (err) => {
                    this.activeDownloads.set(id, {
                        ...this.activeDownloads.get(id),
                        status: 'error',
                        error: err.message
                    });
                    reject(err);
                });
            });
        } catch (err) {
            this.activeDownloads.set(id, {
                status: 'error',
                error: err.message
            });
        }
    }

    getDownloadStatus(id) {
        return this.activeDownloads.get(id);
    }
}

module.exports = new AkwamService();
