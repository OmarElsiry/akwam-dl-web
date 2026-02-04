const API_URL = '/api';

const searchInput = document.getElementById('searchInput');
const typeSelect = document.getElementById('typeSelect');
const resultsDiv = document.getElementById('results');
const detailsDiv = document.getElementById('details');
const loader = document.getElementById('loader');

// Add Enter key support
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

function showLoader() {
    loader.style.display = 'flex';
    resultsDiv.style.opacity = '0.5';
}

function hideLoader() {
    loader.style.display = 'none';
    resultsDiv.style.opacity = '1';
}

async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    showLoader();
    resultsDiv.innerHTML = '';
    detailsDiv.innerHTML = '';

    try {
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}&section=${typeSelect.value}`);
        const data = await response.json();

        if (data.length === 0) {
            resultsDiv.innerHTML = '<p style="text-align:center; grid-column: 1/-1;">No results found.</p>';
        } else {
            data.forEach(item => {
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div class="card-body">
                        <div class="card-title">${item.title}</div>
                    </div>
                `;
                card.onclick = () => loadDetails(item.url, typeSelect.value);
                resultsDiv.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error:', error);
        resultsDiv.innerHTML = `<p style="text-align:center; color:red; grid-column: 1/-1;">Error: ${error.message}</p>`;
    } finally {
        hideLoader();
    }
}

async function loadDetails(url, type) {
    showLoader();
    detailsDiv.innerHTML = '';
    resultsDiv.style.display = 'none'; // Hide results to focus on details

    try {
        // Add "Back" button
        detailsDiv.innerHTML = `<button onclick="goBack()" style="margin-bottom:20px; background:#6c757d;">&larr; Back to Results</button>`;

        if (type === 'movie') {
            const response = await fetch(`${API_URL}/qualities?url=${encodeURIComponent(url)}`);
            const qualities = await response.json();

            const list = document.createElement('div');
            qualities.forEach(q => {
                const item = document.createElement('div');
                item.className = 'episode-item';
                item.innerHTML = `<span>${q.quality} - ${q.size}</span> <span>Download &rarr;</span>`;
                item.onclick = () => resolveLink(q.link, item);
                list.appendChild(item);
            });
            detailsDiv.appendChild(list);
        } else {
            const response = await fetch(`${API_URL}/episodes?url=${encodeURIComponent(url)}`);
            const episodes = await response.json();

            const list = document.createElement('div');
            episodes.forEach(ep => {
                const item = document.createElement('div');
                item.className = 'episode-item';
                item.innerHTML = `<span>${ep.title}</span> <span>Select &rarr;</span>`;
                item.onclick = () => loadDetails(ep.url, 'movie'); // Recursively treat episode as a movie to get qualities
                list.appendChild(item);
            });
            detailsDiv.appendChild(list);
        }
    } catch (error) {
        detailsDiv.innerHTML += `<p style="color:red">Error loading details</p>`;
    } finally {
        hideLoader();
    }
}

async function resolveLink(url, element) {
    const originalText = element.innerHTML;
    element.innerHTML = `<span>Resolution in progress...</span> <div class="loader" style="width:20px; height:20px; border-width:2px;"></div>`;
    element.style.pointerEvents = 'none';

    try {
        const response = await fetch(`${API_URL}/resolve?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        if (data.directLink) {
            window.open(data.directLink, '_blank');
            element.innerHTML = `<span>Resolution Complete!</span> <span style="color:green;">Opened</span>`;
        } else {
            throw new Error('No link found');
        }
    } catch (error) {
        element.innerHTML = `<span>Error resolving link</span> <span style="color:red;">Failed</span>`;
        setTimeout(() => {
            element.innerHTML = originalText;
            element.style.pointerEvents = 'auto';
        }, 2000);
    }
}

function goBack() {
    detailsDiv.innerHTML = '';
    resultsDiv.style.display = 'grid';
}
