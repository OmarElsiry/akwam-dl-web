const axios = require('axios');
const cheerio = require('cheerio');

const BASE_URL = 'https://ak.sv/';

async function getBaseUrl() {
    const response = await axios.get(BASE_URL);
    return response.request.res.responseUrl.replace(/\/$/, '');
}

async function search(query, type = 'movie') {
    const baseUrl = await getBaseUrl();
    const searchUrl = `${baseUrl}/search?q=${query.replace(/ /g, '+')}&section=${type}`;
    console.log(`Searching: ${searchUrl}`);

    const { data } = await axios.get(searchUrl);
    const $ = cheerio.load(data);
    const results = [];

    // Based on Python script: re.findall(rf'({self.url}/{self.type}/\d+/.*?)"', page)
    // Let's look for links that match that pattern
    $('a').each((i, el) => {
        const href = $(el).attr('href');
        if (href && href.includes(`/${type}/`)) {
            const title = $(el).text().trim() || href.split('/').pop().replace(/-/g, ' ');
            results.push({ title, url: href });
        }
    });

    return results;
}

async function runTest() {
    try {
        console.log('--- Testing Batman (Movie) ---');
        const movies = await search('batman', 'movie');
        console.log(movies.slice(0, 5));

        console.log('\n--- Testing Dark (Series) ---');
        const series = await search('dark', 'series');
        console.log(series.slice(0, 5));
    } catch (error) {
        console.error('Error:', error.message);
    }
}

runTest();
