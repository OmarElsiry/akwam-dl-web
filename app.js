const state = {
    results: [],
    type: 'movie',
    currentUrl: '',
    currentEpisodes: [],
    favorites: JSON.parse(localStorage.getItem('akwamFavorites')) || [],
    modalHistory: [],
    showingFavorites: false
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
    modalBackBtn: document.getElementById('modalBackBtn'),
    finalUrl: document.getElementById('finalUrl'),
    favoritesBtn: document.getElementById('favoritesBtn')
};

// --- API Calls ---

window.apiSearch = async function(query, type) {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
    return await res.json();
}

window.apiGetEpisodes = async function(url) {
    const res = await fetch('/api/episodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await res.json();
}

window.apiGetQualities = async function(url) {
    const res = await fetch('/api/qualities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await res.json();
}

window.apiResolve = async function(url) {
    const res = await fetch('/api/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await res.json();
}

window.apiBulkResolve = async function(urls) {
    const res = await fetch('/api/bulk-resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls })
    });
    return await res.json();
}

// --- UI Logic ---

window.showLoading = function(isLoading) {
    dom.loading.style.display = isLoading ? 'flex' : 'none';
}

window.showModalLoading = function(isLoading) {
    dom.modalLoading.style.display = isLoading ? 'flex' : 'none';
}

window.openModal = function(title, disableBack = false) {
    dom.modalTitle.innerText = title;
    dom.modalList.innerHTML = '';
    dom.finalUrl.style.display = 'none';
    dom.overlay.style.display = 'flex';
    
    if (state.modalHistory.length > 0 && !disableBack) {
        dom.modalBackBtn.style.display = 'block';
    } else {
        dom.modalBackBtn.style.display = 'none';
    }
}

dom.modalBackBtn.onclick = () => {
    if (state.modalHistory.length > 0) {
        const prevView = state.modalHistory.pop();
        prevView();
    }
};

dom.closeModal.onclick = () => {
    state.modalHistory = [];
    dom.overlay.style.display = 'none';
};

dom.overlay.onclick = (e) => {
    if (e.target === dom.overlay) {
        state.modalHistory = [];
        dom.overlay.style.display = 'none';
    }
};

window.renderResults = function(results, type) {
    state.showingFavorites = false;
    dom.resultsGrid.innerHTML = '';
    
    if (!results || results.length === 0) {
        dom.resultsGrid.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: var(--text-secondary);">No results found.</p>';
        return;
    }

    results.forEach(item => {
        const isFav = state.favorites.some(f => f.url === item.url);
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-header">
                <span class="type-badge">${type}</span>
                <button class="fav-toggle ${isFav ? 'active' : ''}" onclick="window.toggleFavorite({url: '${item.url}', name: '${item.name.replace(/'/g, "\\'")}'}, '${type}', event)">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                </button>
            </div>
            <h3>${item.name}</h3>
        `;
        div.onclick = (e) => {
             if (e.target.closest('.fav-toggle')) return;
             // Clear modal history on new entry
             state.modalHistory = [];
             window.handleItemClick(item, type);
        };
        dom.resultsGrid.appendChild(div);
    });
}

window.toggleFavorite = function(item, type, e) {
    if (e) e.stopPropagation();
    const idx = state.favorites.findIndex(f => f.url === item.url);
    if (idx >= 0) {
        state.favorites.splice(idx, 1);
    } else {
        state.favorites.push({ ...item, type });
    }
    localStorage.setItem('akwamFavorites', JSON.stringify(state.favorites));
    
    if (state.showingFavorites) {
        window.renderFavorites();
    } else {
        window.renderResults(state.results, state.type);
    }
}

window.renderFavorites = function() {
    state.showingFavorites = true;
    dom.searchInput.value = '';
    dom.resultsGrid.innerHTML = '';
    
    if (state.favorites.length === 0) {
        dom.resultsGrid.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: var(--text-secondary);">No favorites added yet.</p>';
        return;
    }
    
    state.favorites.forEach(item => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-header">
                <span class="type-badge">${item.type}</span>
                <button class="fav-toggle active" onclick="window.toggleFavorite({url: '${item.url}', name: '${item.name.replace(/'/g, "\\'")}'}, '${item.type}', event)">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                </button>
            </div>
            <h3>${item.name}</h3>
        `;
        div.onclick = (e) => {
             if (e.target.closest('.fav-toggle')) return;
             state.modalHistory = [];
             window.handleItemClick(item, item.type);
        };
        dom.resultsGrid.appendChild(div);
    });
}

dom.favoritesBtn.onclick = () => {
    window.renderFavorites();
};

window.handleItemClick = async function(item, type, isBackAction = false) {
    if (type === 'series') {
        window.openModal('Select Episode', !isBackAction && state.modalHistory.length === 0);
        showModalLoading(true);
        // Only fetch if not going back, or if we don't have currentEpisodes cached for this item
        // For simplicity, we'll fetch again or cache by URL
        const data = await window.apiGetEpisodes(item.url);
        state.currentEpisodes = data.episodes;
        showModalLoading(false);

        const currentViewRenderer = () => window.handleItemClick(item, type, true);

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
            const selected = state.currentEpisodes.slice(start - 1, end);
            state.modalHistory.push(currentViewRenderer);
            window.handleBulkResolve(selected);
        };

        state.currentEpisodes.forEach((ep, index) => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerText = \`\${index + 1}. \${ep.name}\`;
            row.onclick = () => {
                state.modalHistory.push(currentViewRenderer);
                window.handleQualitySelect(ep.url);
            }
            dom.modalList.appendChild(row);
        });
    } else {
        const currentViewRenderer = () => window.handleQualitySelect(item.url, true);
        window.handleQualitySelect(item.url);
    }
}

window.handleBulkResolve = async function(episodesToResolve) {
    if (!episodesToResolve || episodesToResolve.length === 0) return;
    window.openModal('Bulk Resolving...');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <p style="margin-bottom: 2rem; color: var(--text-secondary);">Processing ${episodesToResolve.length} episodes in parallel. This may take a few moments...</p>
            <div class="spinner" style="margin: 0 auto;"></div>
        </div>
    `;

    try {
        const data = await window.apiBulkResolve(episodesToResolve);
        if (data.results && data.results.length > 0) {
            const linksText = data.results.map(r => r.url).join('\n');
            const blob = new Blob([linksText], { type: 'text/plain' });
            const downloadUrl = URL.createObjectURL(blob);
            
            dom.modalList.innerHTML = `
                <p style="margin-bottom: 1rem; color: var(--text-secondary);">Done! Successfully resolved ${data.results.length} links.</p>
                <textarea class="links-box" readonly>${linksText}</textarea>
                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                    <button class="btn-primary" style="flex: 1;" onclick="window.copyBulkLinks(this)">COPY ALL</button>
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

window.copyLinkToClipboard = async function(text, btn) {
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

window.copyBulkLinks = function(btn) {
    const textarea = dom.modalList.querySelector('.links-box');
    textarea.select();
    document.execCommand('copy');
    const originalText = btn.innerText;
    btn.innerText = 'COPIED!';
    setTimeout(() => btn.innerText = originalText, 2000);
}

window.handleQualitySelect = async function(url, isBackAction = false) {
    window.openModal('Select Quality', !isBackAction && state.modalHistory.length === 0);
    showModalLoading(true);
    const data = await window.apiGetQualities(url);
    showModalLoading(false);
    
    const currentViewRenderer = () => window.handleQualitySelect(url, true);

    data.qualities.forEach(q => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `
            <span class="quality-tag">${q.quality}</span>
            <span class="size-tag">${q.size}</span>
        `;
        row.onclick = () => {
            state.modalHistory.push(currentViewRenderer);
            window.resolveFinalUrl(q.link_id);
        }
        dom.modalList.appendChild(row);
    });
}

window.playVideo = function(url) {
    state.modalHistory.push(() => window.renderFinalUrlScreen(url));
    dom.modalTitle.innerText = "Playing Video";
    
    // Add enhanced properties to the video element for better UX
    dom.modalList.innerHTML = `
        <div style="padding: 1rem; width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; gap: 1rem; background: #000; border-radius: var(--radius); overflow: hidden;">
            <video controls autoplay playsinline style="width: 100%; max-height: calc(85vh - 100px); outline: none; background: #000; border-radius: var(--radius); object-fit: contain;">
                <source src="${url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
    `;
}

window.renderFinalUrlScreen = function(url) {
    dom.modalTitle.innerText = "Direct Link";
    dom.modalList.innerHTML = `
        <div class="result-container">
            <p class="result-label">Direct Link:</p>
            <div class="link-display-box">
                <code class="raw-url">${url}</code>
                <button class="btn-secondary btn-sm" onclick="window.copyLinkToClipboard('${url}', this)">COPY</button>
            </div>
            
            <div style="margin-top: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem;">
                <a href="${url}" class="btn-primary" style="text-align:center; text-decoration:none;" target="_blank">DOWNLOAD VIA BROWSER</a>
                <button class="btn-secondary" style="border-color: #f39c12; color: #f39c12; background: #fffaf0; padding: 0.85rem;" onclick="window.playVideo('${url}')">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none" style="vertical-align: middle; margin-right: 8px;">
                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                    STREAM IN BROWSER
                </button>
            </div>
        </div>
    `;
}

window.resolveFinalUrl = async function(link_id) {
    window.openModal('Finalizing Link');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2rem;">
            <p style="margin-bottom: 2rem; color: var(--text-secondary);">Securing your direct download link...</p>
            <div class="spinner" style="margin: 0 auto;"></div>
        </div>
    `;

    showModalLoading(true);
    const data = await window.apiResolve(link_id);
    showModalLoading(false);

    if (data.url) {
        window.renderFinalUrlScreen(data.url);
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
    state.results = [];

    try {
        const data = await window.apiSearch(q, type);
        state.results = data.results;
        window.renderResults(data.results, type);
    } catch (e) {
        alert('Error searching. Please try again.');
    } finally {
        showLoading(false);
    }
};

dom.searchType.onchange = () => {
    if (!state.showingFavorites) {
        state.results = [];
        dom.resultsGrid.innerHTML = '';
        state.type = dom.searchType.value;
    }
};

dom.searchInput.onkeypress = (e) => {
    if (e.key === 'Enter') dom.searchBtn.click();
};
