const state = {
    results: [],
    type: 'movie',
    currentUrl: '',
    currentEpisodes: [],
};

const dom = {
    searchBtn: document.getElementById('searchBtn'),
    searchInput: document.getElementById('searchInput'),
    searchType: document.getElementById('searchType'),
    resultsGrid: document.getElementById('resultsGrid'),
    loading: document.getElementById('loading'),
    overlay: document.getElementById('overlay'),
    modalTitle: document.getElementById('modalTitle'),
    modalList: document.getElementById('modalList'),
    modalLoading: document.getElementById('modalLoading'),
    closeModal: document.getElementById('closeModal'),
    finalUrl: document.getElementById('finalUrl'),
};

// --- API Calls ---

async function apiSearch(query, type) {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
    return await res.json();
}

async function apiGetEpisodes(url) {
    const res = await fetch('/api/episodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await res.json();
}

async function apiGetQualities(url) {
    const res = await fetch('/api/qualities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await res.json();
}

async function apiResolve(url) {
    const res = await fetch('/api/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await res.json();
}

async function apiBulkResolve(urls) {
    const res = await fetch('/api/bulk-resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls })
    });
    return await res.json();
}

// --- UI Logic ---

function showLoading(isLoading) {
    dom.loading.style.display = isLoading ? 'flex' : 'none';
}

function showModalLoading(isLoading) {
    dom.modalLoading.style.display = isLoading ? 'flex' : 'none';
}

function openModal(title) {
    dom.modalTitle.innerText = title;
    dom.modalList.innerHTML = '';
    dom.finalUrl.style.display = 'none';
    dom.overlay.style.display = 'flex';
}

dom.closeModal.onclick = () => {
    dom.overlay.style.display = 'none';
};

dom.overlay.onclick = (e) => {
    if (e.target === dom.overlay) dom.overlay.style.display = 'none';
};

function renderResults(results, type) {
    dom.resultsGrid.innerHTML = '';
    results.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <span class="type-badge">${type}</span>
            <h3>${item.name}</h3>
        `;
        div.onclick = () => handleItemClick(item, type);
        dom.resultsGrid.appendChild(div);
    });
}

async function handleItemClick(item, type) {
    if (type === 'series') {
        openModal('Select Episode');
        showModalLoading(true);
        const data = await apiGetEpisodes(item.url);
        state.currentEpisodes = data.episodes;
        showModalLoading(false);

        // Add Bulk Resolve Button
        const bulkBtn = document.createElement('button');
        bulkBtn.className = 'btn-primary';
        bulkBtn.style.width = '100%';
        bulkBtn.style.marginBottom = '1.5rem';
        bulkBtn.innerText = `RESOLVE ALL (${state.currentEpisodes.length} EPISODES)`;
        bulkBtn.onclick = handleBulkResolve;
        dom.modalList.appendChild(bulkBtn);

        state.currentEpisodes.forEach(ep => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerText = ep.name;
            row.onclick = () => handleQualitySelect(ep.url);
            dom.modalList.appendChild(row);
        });
    } else {
        handleQualitySelect(item.url);
    }
}

async function handleBulkResolve() {
    openModal('Bulk Resolving...');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <p style="margin-bottom: 2rem; color: var(--text-dim);">Processing all episodes in parallel. This may take a few moments...</p>
            <div class="spinner" style="margin: 0 auto;"></div>
        </div>
    `;

    try {
        const data = await apiBulkResolve(state.currentEpisodes);
        if (data.results && data.results.length > 0) {
            const linksText = data.results.map(r => `${r.name}: ${r.url}`).join('\n');
            dom.modalList.innerHTML = `
                <p style="margin-bottom: 1rem; color: var(--text-dim);">Done! Successfully resolved ${data.results.length} links.</p>
                <textarea class="links-box" readonly>${linksText}</textarea>
                <button class="btn-primary" style="width:100%; margin-top: 1rem;" onclick="copyBulkLinks(this)">COPY ALL LINKS</button>
            `;
        } else {
            dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center;">Failed to resolve any links. Try again later.</p>';
        }
    } catch (e) {
        dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center;">Error during bulk resolution.</p>';
    }
}

function copyBulkLinks(btn) {
    const textarea = dom.modalList.querySelector('.links-box');
    textarea.select();
    document.execCommand('copy');
    const originalText = btn.innerText;
    btn.innerText = 'COPIED!';
    setTimeout(() => btn.innerText = originalText, 2000);
}

async function handleQualitySelect(url) {
    openModal('Select Quality');
    showModalLoading(true);
    const data = await apiGetQualities(url);
    showModalLoading(false);

    data.qualities.forEach(q => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `
            <span class="quality-tag">${q.quality}</span>
            <span class="size-tag">${q.size}</span>
        `;
        row.onclick = () => resolveFinalUrl(q.link_id);
        dom.modalList.appendChild(row);
    });
}

async function resolveFinalUrl(link_id) {
    dom.modalList.innerHTML = '<p style="text-align:center; padding: 2rem;">Resolving direct link... please wait.</p>';
    showModalLoading(true);
    const data = await apiResolve(link_id);
    showModalLoading(false);

    if (data.url) {
        dom.modalList.innerHTML = `
            <p style="margin-bottom: 1rem; color: #94a3b8;">Your direct link is ready:</p>
            <a href="${data.url}" class="btn-primary" style="display:block; text-align:center; text-decoration:none;" target="_blank">DOWNLOAD NOW</a>
        `;
        dom.finalUrl.innerText = data.url;
        dom.finalUrl.style.display = 'block';
    } else {
        dom.modalList.innerHTML = '<p style="color:var(--danger);">Error resolving link. Please try another quality.</p>';
    }
}

dom.searchBtn.onclick = async () => {
    const q = dom.searchInput.value.trim();
    const type = dom.searchType.value;
    if (!q) return;

    showLoading(true);
    dom.resultsGrid.innerHTML = '';

    try {
        const data = await apiSearch(q, type);
        renderResults(data.results, type);
    } catch (e) {
        alert('Error searching. Please try again.');
    } finally {
        showLoading(false);
    }
};

dom.searchInput.onkeypress = (e) => {
    if (e.key === 'Enter') dom.searchBtn.click();
};
