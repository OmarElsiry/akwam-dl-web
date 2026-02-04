const HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
};

async function test() {
    console.log('Resolving base URL...');
    const initRes = await fetch('https://ak.sv/', { redirect: 'follow', headers: HEADERS });
    const baseUrl = initRes.url.replace(/\/$/, '');
    console.log('Base URL:', baseUrl);

    const query = 'batman';
    const type = 'movie';
    const searchUrl = `${baseUrl}/search?q=${query}&section=${type}&page=1`;
    console.log('Search URL:', searchUrl);

    const res = await fetch(searchUrl, { headers: HEADERS });
    const html = await res.text();
    console.log('HTML Length:', html.length);

    // Check for obvious results
    const results = [];
    const broadRegex = new RegExp(`(https?://[^/]+/${type}/\\d+/.*?)"`, 'g');
    const matches = html.matchAll(broadRegex);
    for (const m of matches) {
        results.push(m[1]);
    }

    console.log('Found URLs:', results.length);
    if (results.length > 0) {
        console.log('Sample Result:', results[0]);
    } else {
        console.log('HTML snippet around search results area:');
        const index = html.indexOf('widget-body');
        if (index !== -1) {
            console.log(html.substring(index, index + 1000));
        } else {
            console.log('Could not find widget-body in HTML. First 500 chars:');
            console.log(html.substring(0, 500));
        }
    }
}

test();
