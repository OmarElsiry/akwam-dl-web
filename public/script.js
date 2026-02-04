const API_BASE = '/api';

// DOM Elements
const searchBtn = document.getElementById('search-btn');
const searchInput = document.getElementById('search-input');
const typeSelect = document.getElementById('type-select');
const resultsGrid = document.getElementById('results-section');
const episodesSection = document.getElementById('episodes-section');
const episodesGrid = document.getElementById('episodes-grid');
const resultsSection = document.getElementById('results-section');
const loader = document.getElementById('loader');
const modal = document.getElementById('modal');
const closeModal = document.querySelector('.close-modal');
const qualityList = document.getElementById('quality-list');
const directUrlInput = document.getElementById('direct-url');
const directLinkContainer = document.getElementById('direct-link-container');
const downloadAnchor = document.getElementById('download-anchor');
const copyBtn = document.getElementById('copy-btn');

// State
let currentType = 'movie';

// Helper: Show/Hide Loader
const toggleLoader = (show) => {
    loader.classList.toggle('hidden', !show);
};

// API: Search
const search = async () => {
    const query = searchInput.value.trim();
    if (!query) return;

    toggleLoader(true);
    currentType = typeSelect.value;

    try {
        const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&type=${currentType}`);
        const data = await response.json();
        renderResults(data);
    } catch (error) {
        console.error('Search error:', error);
        alert('Failed to fetch results.');
    } finally {
        toggleLoader(false);
    }
};

// Render Results
const renderResults = (results) => {
    resultsGrid.innerHTML = '';
    resultsGrid.classList.remove('hidden');
    episodesSection.classList.add('hidden');

    if (results.length === 0) {
        resultsGrid.innerHTML = '<p style="text-align: center; grid-column: 1/-1;">No results found.</p>';
        return;
    }

    results.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="card-content">
                <div class="card-type">${currentType}</div>
                <h3 class="card-title">${item.title}</h3>
            </div>
        `;
        card.addEventListener('click', () => handleItemClick(item));
        resultsGrid.appendChild(card);
    });
};

// Handle Item Click
const handleItemClick = async (item) => {
    if (currentType === 'series') {
        fetchEpisodes(item.url);
    } else {
        fetchQualities(item.url);
    }
};

// API: Fetch Episodes
const fetchEpisodes = async (url) => {
    toggleLoader(true);
    try {
        const response = await fetch(`${API_BASE}/episodes?url=${encodeURIComponent(url)}`);
        const data = await response.json();
        renderEpisodes(data);
    } catch (error) {
        console.error('Episodes error:', error);
    } finally {
        toggleLoader(false);
    }
};

// Render Episodes
const renderEpisodes = (episodes) => {
    resultsGrid.classList.add('hidden');
    episodesSection.classList.remove('hidden');
    episodesGrid.innerHTML = '';

    episodes.forEach(ep => {
        const btn = document.createElement('div');
        btn.className = 'episode-btn';
        btn.textContent = ep.title;
        btn.addEventListener('click', () => fetchQualities(ep.url));
        episodesGrid.appendChild(btn);
    });
};

// API: Fetch Qualities
const fetchQualities = async (url) => {
    toggleLoader(true);
    try {
        const response = await fetch(`${API_BASE}/load?url=${encodeURIComponent(url)}`);
        const data = await response.json();
        showQualityModal(data);
    } catch (error) {
        console.error('Qualities error:', error);
    } finally {
        toggleLoader(false);
    }
};

// Quality Modal
const showQualityModal = (qualities) => {
    qualityList.innerHTML = '';
    directLinkContainer.classList.add('hidden');
    modal.classList.remove('hidden');

    qualities.forEach(q => {
        const item = document.createElement('div');
        item.className = 'quality-item';
        item.innerHTML = `
            <span>${q.quality}</span>
            <span class="size">${q.size}</span>
        `;
        item.addEventListener('click', () => fetchDirectUrl(q.url));
        qualityList.appendChild(item);
    });
};

// API: Fetch Direct URL
const fetchDirectUrl = async (url) => {
    toggleLoader(true);
    try {
        const response = await fetch(`${API_BASE}/direct?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        directUrlInput.value = data.downloadLink;
        downloadAnchor.href = data.downloadLink;
        directLinkContainer.classList.remove('hidden');
    } catch (error) {
        console.error('Direct URL error:', error);
        alert('Failed to get direct link.');
    } finally {
        toggleLoader(false);
    }
};

// Events
searchBtn.addEventListener('click', search);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') search();
});

closeModal.addEventListener('click', () => {
    modal.classList.add('hidden');
});

copyBtn.addEventListener('click', () => {
    directUrlInput.select();
    document.execCommand('copy');
    copyBtn.textContent = 'Copied!';
    setTimeout(() => copyBtn.textContent = 'Copy', 2000);
});

document.getElementById('back-to-results').addEventListener('click', () => {
    resultsGrid.classList.remove('hidden');
    episodesSection.classList.add('hidden');
});

// Click outside modal to close
window.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
});
