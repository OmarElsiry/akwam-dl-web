const express = require('express');
const cors = require('cors');
const path = require('path');
const akwamService = require('./akwamService');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// API Routes

// Search movies or series
app.get('/api/search', async (req, res) => {
    try {
        const { q, type = 'movie', page = 1 } = req.query;

        if (!q) {
            return res.status(400).json({ error: 'Query parameter "q" is required' });
        }

        const results = await akwamService.search(q, type, parseInt(page));
        res.json(results);
    } catch (error) {
        console.error('[API] Search error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Get episodes for a series
app.get('/api/episodes', async (req, res) => {
    try {
        const { url } = req.query;

        if (!url) {
            return res.status(400).json({ error: 'URL parameter is required' });
        }

        const results = await akwamService.getEpisodes(url);
        res.json(results);
    } catch (error) {
        console.error('[API] Episodes error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Get quality options for a movie/episode
app.get('/api/qualities', async (req, res) => {
    try {
        const { url } = req.query;

        if (!url) {
            return res.status(400).json({ error: 'URL parameter is required' });
        }

        const results = await akwamService.getQualities(url);
        res.json(results);
    } catch (error) {
        console.error('[API] Qualities error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Get direct download URL
app.get('/api/direct', async (req, res) => {
    try {
        const { url } = req.query;

        if (!url) {
            return res.status(400).json({ error: 'URL parameter is required' });
        }

        const result = await akwamService.getDirectUrl(url);
        res.json(result);
    } catch (error) {
        console.error('[API] Direct URL error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Get all episodes with direct links (for "Get All" feature)
app.get('/api/all-episodes', async (req, res) => {
    try {
        const { url, quality = '720p' } = req.query;

        if (!url) {
            return res.status(400).json({ error: 'URL parameter is required' });
        }

        const results = await akwamService.getAllEpisodeLinks(url, quality);
        res.json(results);
    } catch (error) {
        console.error('[API] All episodes error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

// Serve index.html for root
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log(`
    ╔═══════════════════════════════════════════╗
    ║         AKWAM-DL Web Server               ║
    ║                                           ║
    ║   Running on: http://localhost:${PORT}       ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝
    `);
});
