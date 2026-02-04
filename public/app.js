// Akwam-DL Frontend Application

const API_BASE = '';  // Same origin

// State
let currentType = 'movie';
let currentResults = [];
let currentSeriesUrl = '';

// DOM Elements
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const movieBtn = document.getElementById('btn-movie');
const seriesBtn = document.getElementById('btn-series');
const resultsSection = document.getElementById('results-section');
const resultsList = document.getElementById('results-list');
const resultsCount = document.getElementById('results-count');
const episodesSection = document.getElementById('episodes-section');
const episodesList = document.getElementById('episodes-list');
const seriesTitle = document.getElementById('series-title');
const qualitiesSection = document.getElementById('qualities-section');
const qualitiesList = document.getElementById('qualities-list');
const movieTitle = document.getElementById('movie-title');
const downloadSection = document.getElementById('download-section');
const downloadList = document.getElementById('download-list');
const qualitySelect = document.getElementById('quality-select');
const getAllBtn = document.getElementById('get-all-btn');
const backToResults = document.getElementById('back-to-results');
const backToResults2 = document.getElementById('back-to-results-2');
const backToEpisodes = document.getElementById('back-to-episodes');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');

// Event Listeners
movieBtn.addEventListener('click', () => setType('movie'));
seriesBtn.addEventListener('click', () => setType('series'));
searchBtn.addEventListener('click', search);
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') search();
});
backToResults.addEventListener('click', showResults);
backToResults2.addEventListener('click', showResults);
backToEpisodes.addEventListener('click', () => {
    hideAllSections();
    episodesSection.classList.remove('hidden');
});
getAllBtn.addEventListener('click', getAllEpisodes);

// Functions
function setType(type) {
    currentType = type;
    movieBtn.classList.toggle('active', type === 'movie');
    seriesBtn.classList.toggle('active', type === 'series');
}

function showLoading() {
    loading.classList.remove('hidden');
    hideError();
}

function hideLoading() {
    loading.classList.add('hidden');
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

function hideError() {
    errorMessage.classList.add('hidden');
}

function hideAllSections() {
    resultsSection.classList.add('hidden');
    episodesSection.classList.add('hidden');
    qualitiesSection.classList.add('hidden');
    downloadSection.classList.add('hidden');
}

function showResults() {
    hideAllSections();
    resultsSection.classList.remove('hidden');
}

async function search() {
    const query = searchInput.value.trim();
    if (!query) return;

    hideAllSections();
    showLoading();
    hideError();

    try {
        const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}&type=${currentType}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentResults = data.results;
        displayResults(data);
    } catch (error) {
        showError(`Search failed: ${error.message}`);
    } finally {
        hideLoading();
    }
}

function displayResults(data) {
    resultsList.innerHTML = '';
    resultsCount.textContent = `(${data.count} results)`;

    if (data.results.length === 0) {
        resultsList.innerHTML = '<p class="no-results">No results found</p>';
        resultsSection.classList.remove('hidden');
        return;
    }

    data.results.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div>
                <div class="title">${index + 1}. ${item.title}</div>
                <div class="url">${item.url}</div>
            </div>
            <span>→</span>
        `;
        div.addEventListener('click', () => selectResult(item));
        resultsList.appendChild(div);
    });

    resultsSection.classList.remove('hidden');
}

async function selectResult(item) {
    if (currentType === 'series') {
        await loadEpisodes(item);
    } else {
        await loadQualities(item);
    }
}

async function loadEpisodes(series) {
    hideAllSections();
    showLoading();

    try {
        currentSeriesUrl = series.url;
        seriesTitle.textContent = series.title;

        const response = await fetch(`${API_BASE}/api/episodes?url=${encodeURIComponent(series.url)}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        displayEpisodes(data);
    } catch (error) {
        showError(`Failed to load episodes: ${error.message}`);
        showResults();
    } finally {
        hideLoading();
    }
}

function displayEpisodes(data) {
    episodesList.innerHTML = '';

    if (data.episodes.length === 0) {
        episodesList.innerHTML = '<p class="no-results">No episodes found</p>';
        episodesSection.classList.remove('hidden');
        return;
    }

    data.episodes.forEach((ep, index) => {
        const div = document.createElement('div');
        div.className = 'episode-item';
        div.innerHTML = `
            <div>
                <div class="title">${index + 1}. ${ep.title}</div>
            </div>
            <span>→</span>
        `;
        div.addEventListener('click', () => loadEpisodeQualities(ep));
        episodesList.appendChild(div);
    });

    episodesSection.classList.remove('hidden');
}

async function loadQualities(item) {
    hideAllSections();
    showLoading();

    try {
        movieTitle.textContent = item.title;

        const response = await fetch(`${API_BASE}/api/qualities?url=${encodeURIComponent(item.url)}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        displayQualities(data);
    } catch (error) {
        showError(`Failed to load qualities: ${error.message}`);
        showResults();
    } finally {
        hideLoading();
    }
}

async function loadEpisodeQualities(episode) {
    hideAllSections();
    showLoading();

    try {
        movieTitle.textContent = episode.title;

        const response = await fetch(`${API_BASE}/api/qualities?url=${encodeURIComponent(episode.url)}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        displayQualities(data, true);
    } catch (error) {
        showError(`Failed to load qualities: ${error.message}`);
        episodesSection.classList.remove('hidden');
    } finally {
        hideLoading();
    }
}

function displayQualities(data, isEpisode = false) {
    qualitiesList.innerHTML = '';

    // Adjust back button behavior
    backToResults2.textContent = isEpisode ? '← Back to Episodes' : '← Back to Results';
    backToResults2.onclick = isEpisode ? () => {
        hideAllSections();
        episodesSection.classList.remove('hidden');
    } : showResults;

    if (data.qualities.length === 0) {
        qualitiesList.innerHTML = '<p class="no-results">No quality options found</p>';
        qualitiesSection.classList.remove('hidden');
        return;
    }

    data.qualities.forEach((q) => {
        const div = document.createElement('div');
        div.className = 'quality-item';
        div.innerHTML = `
            <div class="quality-info">
                <span class="quality-badge">${q.quality}</span>
                <span class="size">${q.size || 'Unknown size'}</span>
            </div>
            <a href="${q.link}" target="_blank" rel="noopener noreferrer">Open Link</a>
        `;
        qualitiesList.appendChild(div);
    });

    qualitiesSection.classList.remove('hidden');
}

async function getAllEpisodes() {
    if (!currentSeriesUrl) return;

    hideAllSections();
    showLoading();

    const quality = qualitySelect.value;

    try {
        const response = await fetch(`${API_BASE}/api/all-episodes?url=${encodeURIComponent(currentSeriesUrl)}&quality=${quality}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        displayAllDownloads(data);
    } catch (error) {
        showError(`Failed to get all episodes: ${error.message}`);
        episodesSection.classList.remove('hidden');
    } finally {
        hideLoading();
    }
}

function displayAllDownloads(data) {
    downloadList.innerHTML = '';
    backToEpisodes.textContent = '← Back to Episodes';

    if (data.episodes.length === 0) {
        downloadList.innerHTML = '<p class="no-results">No downloads found</p>';
        downloadSection.classList.remove('hidden');
        return;
    }

    data.episodes.forEach((ep, index) => {
        const div = document.createElement('div');
        div.className = 'download-item';

        let linksHtml = '';
        if (ep.success && ep.directUrl) {
            linksHtml = `<a href="${ep.directUrl}" class="success" target="_blank">Direct Download (${ep.quality})</a>`;
        } else if (ep.fallbackUrl) {
            linksHtml = `<a href="${ep.fallbackUrl}" class="warning" target="_blank">Fallback Link (${ep.quality})</a>`;
            if (ep.error) {
                linksHtml += `<span class="error">${ep.error}</span>`;
            }
        } else {
            linksHtml = `<span class="error">${ep.error || 'No link available'}</span>`;
        }

        div.innerHTML = `
            <div class="title">${index + 1}. ${ep.title}</div>
            <div class="links">
                ${linksHtml}
            </div>
        `;
        downloadList.appendChild(div);
    });

    downloadSection.classList.remove('hidden');
}
