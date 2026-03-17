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

        // Add Bulk Resolve Section
        const bulkDiv = document.createElement('div');
        bulkDiv.style.marginBottom = '1.5rem';
        bulkDiv.style.padding = '1rem';
        bulkDiv.style.backgroundColor = 'var(--bg-secondary)';
        bulkDiv.style.borderRadius = 'var(--radius)';
        bulkDiv.style.display = 'flex';
        bulkDiv.style.flexDirection = 'column';
        bulkDiv.style.gap = '0.5rem';

        bulkDiv.innerHTML = `
            <div style="display: flex; gap: 0.5rem; justify-content: space-between; align-items: center;">
                <label style="color: var(--text-secondary); font-size: 0.85rem;">From Ep:</label>
                <input type="number" id="bulkStart" value="1" min="1" max="${state.currentEpisodes.length}" style="width: 60px; padding: 0.25rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--bg-primary); color: white;">
                <label style="color: var(--text-secondary); font-size: 0.85rem;">To Ep:</label>
                <input type="number" id="bulkEnd" value="${state.currentEpisodes.length}" min="1" max="${state.currentEpisodes.length}" style="width: 60px; padding: 0.25rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--bg-primary); color: white;">
            </div>
            <button class="btn-primary" id="btnBulkResolve" style="width: 100%; margin-top: 0.5rem;">RESOLVE SELECTED EPISODES</button>
        `;
        dom.modalList.appendChild(bulkDiv);

        document.getElementById('btnBulkResolve').onclick = () => {
            let start = parseInt(document.getElementById('bulkStart').value) || 1;
            let end = parseInt(document.getElementById('bulkEnd').value) || state.currentEpisodes.length;
            if (start > end) {
                const temp = start;
                start = end;
                end = temp;
            }
            // For example, start=1 means index 0. So slice(start-1, end)
            // But episode numbers might not map exactly to array indices if they are reversed.
            // Let's assume the array is in some order and we just pick slice(start-1, end).
            // Usually Akwam eps are ordered 1..N or N..1.
            // Users visually see the list, but let's just slice the array.
            const selected = state.currentEpisodes.slice(start - 1, end);
            handleBulkResolve(selected);
        };

        state.currentEpisodes.forEach((ep, index) => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerText = `${index + 1}. ${ep.name}`;
            row.onclick = () => handleQualitySelect(ep.url);
            dom.modalList.appendChild(row);
        });
    } else {
        handleQualitySelect(item.url);
    }
}

async function handleBulkResolve(episodesToResolve) {
    if (!episodesToResolve || episodesToResolve.length === 0) return;
    openModal('Bulk Resolving...');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <p style="margin-bottom: 2rem; color: var(--text-secondary);">Processing ${episodesToResolve.length} episodes in parallel. This may take a few moments...</p>
            <div class="spinner" style="margin: 0 auto;"></div>
        </div>
    `;

    try {
        const data = await apiBulkResolve(episodesToResolve);
        if (data.results && data.results.length > 0) {
            const linksText = data.results.map(r => r.url).join('\n');
            const blob = new Blob([linksText], { type: 'text/plain' });
            const downloadUrl = URL.createObjectURL(blob);
            
            dom.modalList.innerHTML = `
                <p style="margin-bottom: 1rem; color: var(--text-secondary);">Done! Successfully resolved ${data.results.length} links.</p>
                <textarea class="links-box" readonly>${linksText}</textarea>
                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                    <button class="btn-primary" style="flex: 1;" onclick="copyBulkLinks(this)">COPY ALL</button>
                    <a href="${downloadUrl}" download="resolved_links.txt" class="btn-secondary" style="flex: 1; text-align: center; text-decoration: none; padding: 0.75rem 1rem;">DOWNLOAD .TXT</a>
                </div>
            `;
        } else {
            dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center;">Failed to resolve any links. Try again later.</p>';
        }
    } catch (e) {
        dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center;">Error during bulk resolution.</p>';
    }
}

async function copyLinkToClipboard(text, btn) {
    try {
        await navigator.clipboard.writeText(text);
        const originalText = btn.innerText;
        btn.innerText = 'COPIED!';
        btn.classList.add('btn-success');
        setTimeout(() => {
            btn.innerText = originalText;
            btn.classList.remove('btn-success');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy: ', err);
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

function playVideo(url) {
    dom.modalList.innerHTML = `
        <div style="padding: 1rem; width: 100%; height: 100%; display: flex; flex-direction: column; gap: 1rem;">
            <button class="btn-secondary" onclick="DOM_restoreUrl('${url}')">BACK</button>
            <video controls autoplay style="width: 100%; max-height: 70vh; background: #000; border-radius: var(--radius);">
                <source src="${url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
    `;
}

function DOM_restoreUrl(url) {
    renderFinalUrlScreen(url);
}

function renderFinalUrlScreen(url) {
    dom.modalList.innerHTML = `
        <div class="result-container">
            <p class="result-label">Direct Link:</p>
            <div class="link-display-box">
                <code class="raw-url">${url}</code>
                <button class="btn-secondary btn-sm" onclick="copyLinkToClipboard('${url}', this)">COPY</button>
            </div>
            
            <div style="margin-top: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem;">
                <a href="${url}" class="btn-primary" style="text-align:center; text-decoration:none;" target="_blank">DOWNLOAD VIA BROWSER</a>
                <button class="btn-secondary" style="border-color: #f39c12; color: #f39c12;" onclick="playVideo('${url}')">STREAM IN BROWSER</button>
                <a href="vlc://${url}" class="btn-secondary" style="text-align:center; text-decoration:none; border-color: #e67e22; color: #e67e22;">PLAY IN VLC</a>
            </div>
        </div>
    `;
}

async function resolveFinalUrl(link_id) {
    openModal('Finalizing Link');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <p style="margin-bottom: 2rem; color: var(--text-secondary);">Securing your direct download link...</p>
            <div class="spinner" style="margin: 0 auto;"></div>
        </div>
    `;

    showModalLoading(true);
    const data = await apiResolve(link_id);
    showModalLoading(false);

    if (data.url) {
        renderFinalUrlScreen(data.url);
    } else {
        dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center; padding: 2rem;">Error resolving link. Please try another quality.</p>';
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

dom.searchType.onchange = () => {
    state.results = [];
    dom.resultsGrid.innerHTML = '';
    state.type = dom.searchType.value;
};

dom.searchInput.onkeypress = (e) => {
    if (e.key === 'Enter') dom.searchBtn.click();
};

