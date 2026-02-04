const searchInput = document.getElementById('searchInput');
const typeSelect = document.getElementById('typeSelect');
const searchBtn = document.getElementById('searchBtn');
const resultsList = document.getElementById('resultsList');
const loader = document.getElementById('loader');
const detailView = document.getElementById('detailView');
const resultsArea = document.getElementById('resultsArea');
const detailTitle = document.getElementById('detailTitle');
const detailContent = document.getElementById('detailContent');
const backBtn = document.getElementById('backBtn');

// UIUX: Listen for Enter key
searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch(searchInput.value, typeSelect.value);
});

searchBtn.addEventListener('click', () => performSearch(searchInput.value, typeSelect.value));
backBtn.addEventListener('click', showSearch);

async function performSearch(query, type) {
    if (!query) return;

    showLoader(true);
    resultsList.innerHTML = '';

    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
        const data = await res.json();

        showLoader(false);
        if (data.error) throw new Error(data.error);

        if (data.length === 0) {
            resultsList.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 4rem;"><p style="font-size: 1.5rem; opacity: 0.5;">No results matched your query. Perhaps check the spelling?</p></div>';
            return;
        }

        data.forEach(item => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="card-badge">${type.toUpperCase()}</div>
                <h3>${item.title}</h3>
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 10px;">Click to view availability</p>
            `;
            card.onclick = () => handleItemClick(item, type);
            resultsList.appendChild(card);
        });
    } catch (err) {
        showLoader(false);
        resultsList.innerHTML = `<div style="grid-column: 1/-1; color: #ff4444; text-align: center; padding: 2rem; background: rgba(255,0,0,0.1); border-radius: 12px; border: 1px solid rgba(255,0,0,0.2);">
            <strong>Architectural Interrupt:</strong> ${err.message}
        </div>`;
    }
}

async function handleItemClick(item, type) {
    showDetail(item.title);
    detailContent.innerHTML = '<div id="loader">SYNCHRONIZING CONTENT...</div>';

    try {
        if (type === 'series') {
            const res = await fetch(`/api/episodes?url=${encodeURIComponent(item.url)}`);
            const episodes = await res.json();
            renderEpisodes(episodes);
        } else {
            const res = await fetch(`/api/qualities?url=${encodeURIComponent(item.url)}`);
            const qualities = await res.json();
            renderQualities(qualities);
        }
    } catch (err) {
        detailContent.innerHTML = `<p style="color:red">Error encountered: ${err.message}</p>`;
    }
}

function renderEpisodes(episodes) {
    detailContent.innerHTML = '<h3 style="color: var(--accent-color); font-size: 1.5rem; margin-bottom: 1.5rem;">EPISODE SELECTION</h3><div class="episode-grid"></div>';
    const grid = detailContent.querySelector('.episode-grid');

    if (episodes.length === 0) {
        detailContent.innerHTML += '<p>No episodes indexed yet.</p>';
        return;
    }

    episodes.forEach((ep, idx) => {
        const card = document.createElement('div');
        card.className = 'ep-card';
        card.innerText = ep.title.replace('الحلقة', 'EP'); // Localization fix for cleaner UI
        card.onclick = async () => {
            detailContent.innerHTML = `<div id="loader">EXTRACTING LINKS FOR ${ep.title.toUpperCase()}...</div>`;
            const res = await fetch(`/api/qualities?url=${encodeURIComponent(ep.url)}`);
            const qualities = await res.json();
            renderQualities(qualities);
        };
        grid.appendChild(card);
    });
}

function renderQualities(qualities) {
    detailContent.innerHTML = '<h3 style="color: var(--accent-color); font-size: 1.5rem; margin-bottom: 1.5rem;">AVAILABLE QUALITIES</h3><ul class="quality-list"></ul>';
    const list = detailContent.querySelector('.quality-list');

    if (!qualities || qualities.length === 0) {
        detailContent.innerHTML += '<div style="padding: 2rem; background: rgba(255,255,255,0.05); border-radius: 12px; opacity: 0.6;">No download channels mapped for this title at this time.</div>';
        return;
    }

    qualities.forEach(q => {
        const li = document.createElement('li');
        li.className = 'quality-item';
        li.innerHTML = `
            <div>
                <span style="font-size: 1.2rem; font-weight: 800; color: white;">${q.quality}</span>
                <span style="color: var(--text-secondary); margin-left: 10px; font-size: 0.9rem;">— SIZE: ${q.size}</span>
            </div>
            <button class="dl-btn" onclick="resolveLink('${q.link}', event)">GENERATE ACCESS LINK</button>
        `;
        list.appendChild(li);
    });
}

async function resolveLink(link, event) {
    const btn = event.currentTarget;
    const originalText = btn.innerText;
    btn.innerText = 'NEGOTIATING...';
    btn.disabled = true;

    try {
        const res = await fetch(`/api/resolve?url=${encodeURIComponent(link)}`);
        const data = await res.json();

        if (data.directLink) {
            btn.innerText = 'ACCESS GRANTED';
            window.open(data.directLink, '_blank');
        } else {
            alert('Protocol Violation: Could not resolve direct download route.');
        }
    } catch (err) {
        alert('Internal System Error: ' + err.message);
    } finally {
        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
        }, 1000);
    }
}

function showLoader(show) {
    loader.classList.toggle('hidden', !show);
    if (show) resultsList.innerHTML = '';
}

function showDetail(title) {
    detailTitle.innerText = title.toUpperCase();
    resultsArea.classList.add('hidden');
    detailView.classList.remove('hidden');
    document.querySelector('.search-section').classList.add('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showSearch() {
    resultsArea.classList.remove('hidden');
    detailView.classList.add('hidden');
    document.querySelector('.search-section').classList.remove('hidden');
}

console.log('%c AKWAM PREMIER BYPASS SYSTEM v2.0 ', 'background: #222; color: #0088ff; font-weight: bold;');
