const axios = require('axios');
const cheerio = require('cheerio');

const client = axios.create({
    timeout: 15000,
    maxRedirects: 10,
    headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
});

async function test() {
    const url = "https://ak.sv/series/477/dark-%D8%A7%D9%84%D9%85%D9%88%D8%B3%D9%85-%D8%A7%D9%84%D8%A7%D9%88%D9%84";
    console.log(`Fetching: ${url}`);
    try {
        const res = await client.get(url);
        console.log(`Status: ${res.status}`);
        console.log(`URL: ${res.request.res.responseUrl}`);
        console.log(`Data length: ${res.data.length}`);

        const $ = cheerio.load(res.data);
        const baseUrl = 'https://ak.sv';
        const regex = new RegExp(`(${baseUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/episode/\\d+/[^"]+)"`, 'g');
        const matches = [...res.data.matchAll(regex)];
        console.log(`Matches found: ${matches.length}`);
        if (matches.length > 0) {
            console.log(`First match: ${matches[0][1]}`);
        }
    } catch (err) {
        console.error(`Error: ${err.message}`);
        if (err.response) {
            console.error(`Response data: ${err.response.data.substring(0, 500)}`);
        }
    }
}

test();
