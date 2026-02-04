const express = require('express');
const cors = require('cors');
const path = require('path');
const akwamService = require('./akwamService');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/search', async (req, res) => {
    const { q, type } = req.query;
    if (!q) return res.status(400).json({ error: 'Query is required' });
    try {
        const results = await akwamService.search(q, type || 'movie');
        res.json(results);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/episodes', async (req, res) => {
    const { url } = req.query;
    if (!url) return res.status(400).json({ error: 'URL is required' });
    try {
        const episodes = await akwamService.getEpisodes(url);
        res.json(episodes);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/qualities', async (req, res) => {
    const { url } = req.query;
    if (!url) return res.status(400).json({ error: 'URL is required' });
    try {
        const qualities = await akwamService.getDownloadLinks(url);
        res.json(qualities);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/resolve', async (req, res) => {
    const { url } = req.query;
    if (!url) return res.status(400).json({ error: 'URL is required' });
    try {
        const directLink = await akwamService.resolveDirectLink(url);
        res.json({ directLink });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/download', async (req, res) => {
    const { url, name } = req.body;
    if (!url || !name) return res.status(400).json({ error: 'URL and Name are required' });
    try {
        const directLink = await akwamService.resolveDirectLink(url);
        const downloadId = await akwamService.downloadFile(directLink, name);
        res.json({ downloadId });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/download-status', (req, res) => {
    const { id } = req.query;
    const status = akwamService.getDownloadStatus(id);
    if (!status) return res.status(404).json({ error: 'Download not found' });
    res.json(status);
});

// To fulfill user's specific request for Batman and Dark
app.get('/api/test-user-request', async (req, res) => {
    try {
        const batman = await akwamService.search('batman', 'movie');
        const dark = await akwamService.search('dark', 'series');
        res.json({ batman: batman.slice(0, 5), dark: dark.slice(0, 5) });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
