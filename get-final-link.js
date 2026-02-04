const akwamService = require('./akwamService');

async function getBatmanFinalLink() {
    try {
        console.log('--- Step 1: Searching for "Batman" ---');
        const movies = await akwamService.search('batman', 'movie');
        if (movies.length === 0) throw new Error('No movies found');

        const movie = movies[0];
        console.log(`Found Movie: ${movie.title}`);
        console.log(`Movie page: ${movie.url}`);

        console.log('\n--- Step 2: Fetching Qualities ---');
        const qualities = await akwamService.getDownloadLinks(movie.url);
        if (qualities.length === 0) throw new Error('No qualities found');

        const selectedQuality = qualities[0];
        console.log(`Selected Quality: ${selectedQuality.quality} (${selectedQuality.size})`);
        console.log(`Intermediate Link: ${selectedQuality.link}`);

        console.log('\n--- Step 3: Resolving Final Direct Link ---');
        const directLink = await akwamService.resolveDirectLink(selectedQuality.link);

        console.log('\n=========================================');
        console.log('🎉 FINAL DOWNLOAD LINK:');
        console.log(directLink);
        console.log('=========================================');

    } catch (err) {
        console.error('❌ Error during resolution:', err.message);
    }
}

getBatmanFinalLink();
