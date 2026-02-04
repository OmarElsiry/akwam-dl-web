const akwamService = require('./akwamService');
const cheerio = require('cheerio');

async function debugSearch() {
    try {
        console.log('--- Debugging Akwam Homepage ---');
        const baseUrl = await akwamService.init();
        const { data } = await akwamService.request(baseUrl);

        const $ = cheerio.load(data);
        const forms = [];
        $('form').each((i, el) => {
            forms.push({
                action: $(el).attr('action'),
                method: $(el).attr('method'),
                inputs: $(el).find('input').map((j, input) => ({
                    name: $(input).attr('name'),
                    type: $(input).attr('type')
                })).get()
            });
        });

        console.log('Detected Forms:', JSON.stringify(forms, null, 2));

    } catch (error) {
        console.error('Debug Error:', error.message);
    }
}

debugSearch();
