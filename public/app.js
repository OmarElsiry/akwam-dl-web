const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:3000/api' : '/api';

let currentType = 'movie';

const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resultsGrid = document.getElementById('resultsGrid');
const statusMessage = document.getElementById('statusMessage');
const modal = document.getElementById('detailModal');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');

// Event Listeners
searchBtn.addEventListener('click', () => performSearch());
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});

function switchTab(type) {
    currentType = type;

    // Update UI tabs
    document.querySelectorAll('.nav-links li').forEach(el => {
        el.classList.remove('active');
        if (el.dataset.type === type) el.classList.add('active');
    });

    // Clear current results
    resultsGrid.innerHTML = '';
    statusMessage.textContent = `Ready to search in ${type === 'movie' ? 'Movies' : 'Series'} database.`;
    statusMessage.classList.remove('hidden');
}

async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    showStatus('Searching database...');
    resultsGrid.innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&type=${currentType}`);
        if (!res.ok) throw new Error('Search failed');

        const data = await res.json();

        if (data.length === 0) {
            showStatus('No results found.');
            return;
        }

        hideStatus();
        data.forEach(item => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h3>${item.title}</h3>
                <div class="meta">${currentType.toUpperCase()}</div>
            `;
            card.onclick = () => openDetail(item);
            resultsGrid.appendChild(card);
        });

    } catch (err) {
        showStatus(`Error: ${err.message}`);
    }
}

async function openDetail(item) {
    modal.classList.remove('hidden');
    modalTitle.textContent = item.title;
    modalBody.innerHTML = '<div class="status-message">Loading details...</div>';

    try {
        let endpoint = currentType === 'movie' ? 'qualities' : 'episodes';
        const res = await fetch(`${API_BASE}/${endpoint}?url=${encodeURIComponent(item.url)}`);
        const data = await res.json();

        modalBody.innerHTML = '';

        if (data.length === 0) {
            modalBody.innerHTML = '<div class="status-message">No content found.</div>';
            return;
        }

        if (currentType === 'movie') {
            // Render Qualities
            data.forEach(q => {
                const row = document.createElement('div');
                row.className = 'list-item';
                row.innerHTML = `
                    <span>${q.quality} <span class="quality-badge">${q.size}</span></span>
                    <button onclick="resolveLink('${q.link}')">Get Link</button>
                `;
                modalBody.appendChild(row);
            });
        } else {
            // Render Episodes
            data.forEach(ep => {
                const row = document.createElement('div');
                row.className = 'list-item';
                row.innerHTML = `
                    <span>${ep.title}</span>
                    <button onclick="fetchQualities('${ep.url}')">View</button>
                `;
                modalBody.appendChild(row);
            });
        }

    } catch (err) {
        modalBody.innerHTML = `<div class="status-message error">Failed to load: ${err.message}</div>`;
    }
}

async function fetchQualities(url) {
    modalBody.innerHTML = '<div class="status-message">Loading links...</div>';
    try {
        const res = await fetch(`${API_BASE}/qualities?url=${encodeURIComponent(url)}`);
        const data = await res.json();

        modalBody.innerHTML = ''; // Clear loading

        // Add a "Back" button roughly (by clearing and reloading episodes? No, simple list for now)
        const backBtn = document.createElement('div');
        backBtn.className = 'list-item';
        backBtn.innerHTML = '<strong>Download Links</strong>';
        modalBody.appendChild(backBtn);

        data.forEach(q => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerHTML = `
                <span>${q.quality} <span class="quality-badge">${q.size}</span></span>
                <button onclick="resolveLink('${q.link}')">Get Link</button>
            `;
            modalBody.appendChild(row);
        });
    } catch (err) {
        modalBody.innerHTML = `<div class="status-message error">Error: ${err.message}</div>`;
    }
}

async function resolveLink(url) {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Resolving...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/resolve?url=${encodeURIComponent(url)}`);
        const data = await res.json();

        if (data.directLink) {
            window.open(data.directLink, '_blank');
            btn.textContent = 'Opened!';
        } else {
            throw new Error('No link returned');
        }
    } catch (err) {
        alert('Failed to resolve link: ' + err.message);
        btn.textContent = 'Failed';
    } finally {
        setTimeout(() => {
            btn.textContent = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

function closeModal() {
    modal.classList.add('hidden');
}

function showStatus(msg) {
    statusMessage.textContent = msg;
    statusMessage.classList.remove('hidden');
}

function hideStatus() {
    statusMessage.classList.add('hidden');
}

// Close modal on outside click
window.onclick = function (event) {
    if (event.target == modal) {
        closeModal();
    }
}
