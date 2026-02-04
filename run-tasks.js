const akwamService = require('./akwamService');

async function runTasks() {
    try {
        console.log('--- TASK 1: Get movie called "Batman" ---');
        const movies = await akwamService.search('batman', 'movie');
        console.log(`Found ${movies.length} movies.`);
        if (movies.length > 0) {
            const first = movies[0];
            console.log(`Selected: ${first.title} (${first.url})`);
            const qualities = await akwamService.getDownloadLinks(first.url);
            console.log('Qualities:', qualities);
        }

        console.log('\n--- TASK 2: Get series called "Dark" (whole season) ---');
        const series = await akwamService.search('dark', 'series');
        console.log(`Found ${series.length} series.`);
        const darkSeries = series.find(s => s.title.toLowerCase().includes('dark')) || series[0];
        if (darkSeries) {
            console.log(`Selected: ${darkSeries.title} (${darkSeries.url})`);
            const episodes = await akwamService.getEpisodes(darkSeries.url);
            console.log(`Found ${episodes.length} episodes.`);
            console.log('First 3 episodes:', episodes.slice(0, 3).map(e => e.title));

            // To be thorough, resolve one link from the first episode
            const firstEp = episodes[0];
            const qualities = await akwamService.getDownloadLinks(firstEp.url);
            console.log(`Qualities for ${firstEp.title}:`, qualities);
        }

    } catch (err) {
        console.error('Task failed:', err.message);
    }
}

runTasks();
