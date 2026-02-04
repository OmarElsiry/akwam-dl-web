const akwamService = require('./akwamService');

async function bruteSearch() {
    const baseUrl = await akwamService.init();
    const query = 'dark';
    const tests = [
        { url: `${baseUrl}/search?q=${query}`, method: 'get' },
        { url: `${baseUrl}/search/${query}`, method: 'get' },
        { url: `${baseUrl}/search`, method: 'get', params: { q: query } },
        { url: `${baseUrl}/explore?q=${query}`, method: 'get' },
        { url: `${baseUrl}/search`, method: 'post', data: `q=${query}`, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ];

    for (const test of tests) {
        try {
            console.log(`Testing ${test.method.toUpperCase()} ${test.url}...`);
            const config = { headers: test.headers || {} };
            let res;
            if (test.method === 'get') {
                res = await akwamService.request(test.url, config);
            } else {
                // For post, we'll need to update request or use axios directly for this test
                // But let's try GETs first
                continue;
            }
            console.log(`SUCCESS [${res.status}] - Length: ${res.data.length}`);
            if (res.data.includes('/movie/') || res.data.includes('/series/')) {
                console.log('Found results in HTML!');
                return;
            }
        } catch (error) {
            console.log(`FAILED [${error.response ? error.response.status : error.code}] - ${error.message}`);
        }
    }
}

bruteSearch();
