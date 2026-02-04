const { AkwamAPI } = require('./lib/akwam.js');

async function test() {
    const api = new AkwamAPI();
    console.log("Searching for Batman...");
    const results = await api.search("batman");
    console.log(`Found ${results.length} results.`);
    if (results.length > 0) {
        console.log(`First result: ${results[0].name} -> ${results[0].url}`);

        console.log("Fetching qualities...");
        const qualities = await api.getQualities(results[0].url);
        console.log(`Qualities:`, qualities);

        if (qualities.length > 0) {
            console.log("Fetching direct URL...");
            const direct = await api.getDirectUrl(qualities[0].link);
            console.log(`Direct URL: ${direct}`);
        }
    }

    console.log("\nSearching for Dark...");
    const series = await api.search("dark", "series");
    const darkSeason1 = series.find(s => s.name === "Dark الموسم الاول" || s.name === "Dark Season 1");
    if (darkSeason1) {
        console.log(`Found: ${darkSeason1.name} -> ${darkSeason1.url}`);
        const episodes = await api.fetchEpisodes(darkSeason1.url);
        console.log(`Found ${episodes.length} episodes.`);
        if (episodes.length > 0) {
            console.log(`First episode: ${episodes[0].name}`);
        }
    } else {
        console.log("Dark Season 1 not found in top results. Matches:", series.map(s => s.name));
    }
}

test().catch(console.error);
