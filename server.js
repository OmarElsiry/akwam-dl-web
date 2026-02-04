const express = require('express');
const axios = require('axios');
const cheerio = require('cheerio');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

const HTTP = 'https://';
let BASE_URL = 'https://akwam.site'; // Fallback

const getAkwamBase = async () => {
    try {
        const response = await axios.get('https://ak.sv/');
        return response.request.res.responseUrl.replace(/\/$/, '');
    } catch (error) {
        console.error('Error resolving Akwam URL:', error);
        return 'https://akwam.site';
    }
};

app.get('/api/search', async (req, res) => {
    const { q, type = 'movie' } = req.query;
    try {
        const baseUrl = await getAkwamBase();
        const searchUrl = `${baseUrl}/search?q=${q.replace(/ /g, '+')}&section=${type}`;
        const { data } = await axios.get(searchUrl);
        const $ = cheerio.load(data);

        const results = [];
        $(`a[href^="${baseUrl}/${type}/"]`).each((i, el) => {
            const href = $(el).attr('href');
            const title = href.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            results.push({ title, url: href });
        });

        // Remove duplicates and reverse as in python script
        const uniqueResults = [...new Map(results.map(item => [item.url, item])).values()].reverse();
        res.json(uniqueResults);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/episodes', async (req, res) => {
    const { url } = req.query;
    try {
        const baseUrl = await getAkwamBase();
        const { data } = await axios.get(url);
        const $ = cheerio.load(data);

        const episodes = [];
        $(`a[href^="${baseUrl}/episode/"]`).each((i, el) => {
            const href = $(el).attr('href');
            const title = href.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            episodes.push({ title, url: href });
        });

        res.json(episodes.reverse());
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/load', async (req, res) => {
    const { url } = req.query;
    try {
        const { data } = await axios.get(url);
        const $ = cheerio.load(data);

        const qualities = [];
        $('.tab-content.quality').each((i, el) => {
            const $el = $(el);
            const qualityText = $el.find('span').first().text().trim() || 'Download';
            const dlLink = $el.find('a[href*="/link/"]').attr('href');
            const size = $el.find('.font-size-14.mr-auto').text().trim();

            if (dlLink) {
                qualities.push({ quality: qualityText, url: dlLink, size });
            }
        });

        res.json(qualities);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/direct', async (req, res) => {
    const { url } = req.query;
    try {
        // The url passed here is the /link/ URL
        // Step 1: Solving shortened URL
        const res1 = await axios.get(url.startsWith('http') ? url : `https://${url}`);
        const $1 = cheerio.load(res1.data);
        const shortenUrl = $1('a[href*="/download/"]').attr('href');

        if (!shortenUrl) throw new Error('Could not find download link');

        // Step 2: Getting Direct URL
        const res2 = await axios.get(shortenUrl.startsWith('http') ? shortenUrl : `https://${shortenUrl}`);
        const finalUrl = res2.request.res.responseUrl;

        // Step 3: Extract the direct file link from the final page
        const $2 = cheerio.load(res2.data);
        // Look for the actual download button/link
        let downloadLink = $2('a.download-link').attr('href') || $2('a[href*="/download/"]').attr('href');

        // The original python script uses regex: RGX_DIRECT_URL = r'([a-z0-9]{4,}\.\w+\.\w+/download/.*?)"'
        // Let's try to match that if cheerio fails
        if (!downloadLink) {
            const match = res2.data.match(/([a-z0-9]{4,}\.\w+\.\w+\/download\/.*?)"/);
            if (match) downloadLink = 'https://' + match[1];
        }

        res.json({ downloadLink: downloadLink || finalUrl });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
