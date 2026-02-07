const state = {
    results: [],
    type: 'movie',
    currentUrl: '',
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
        showModalLoading(false);

        data.episodes.forEach(ep => {
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
