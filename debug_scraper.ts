import { AkwamAPI } from './lib/akwam';

async function test() {
    const api = new AkwamAPI();
    const query = 'batman';
    console.log(`Searching for: ${query}`);

    // Patching initialize to log the base URL
    const results = await api.search(query);

    console.log('Results sequence length:', results.length);
    if (results.length === 0) {
        console.log('NO RESULTS FOUND. Checking why...');
        // We might need to log the HTML inside search to really know.
    } else {
        results.forEach(r => console.log(`- ${r.name}: ${r.url}`));
    }
}

test().catch(console.error);
