const state = {
    results: [],
    type: 'movie', // Default type
    currentUrl: '',
    currentEpisodes: [],
    favorites: JSON.parse(localStorage.getItem('vortexFavorites')) || [],
    modalHistory: []
};

const dom = {
    searchBtn: document.getElementById('searchBtn'),
    searchInput: document.getElementById('searchInput'),
    resultsGrid: document.getElementById('resultsGrid'),
    loading: document.getElementById('loading'),
    overlay: document.getElementById('overlay'),
    modalTitle: document.getElementById('modalTitle'),
    modalList: document.getElementById('modalList'),
    modalLoading: document.getElementById('modalLoading'),
    closeModal: document.getElementById('closeModal'),
    modalBackBtn: document.getElementById('modalBackBtn'),
    finalUrl: document.getElementById('finalUrl'),
    favoritesBtn: document.getElementById('favoritesBtn'),
    
    // Switch elements
    searchTypeSwitch: document.getElementById('searchTypeSwitch'),
    switchOpts: document.querySelectorAll('.switch-opt'),
    
    // Drawer elements
    drawer: document.getElementById('drawer'),
    drawerOverlay: document.getElementById('drawerOverlay'),
    favoritesList: document.getElementById('favoritesList'),
    closeDrawer: document.getElementById('closeDrawer')
};

// --- Initialization ---

// Initialize switch listeners
dom.switchOpts.forEach(opt => {
    opt.onclick = () => {
        dom.switchOpts.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        state.type = opt.dataset.value;
        
        // Optional: Clear results when switching type to keep it clean
        state.results = [];
        dom.resultsGrid.innerHTML = '';
    };
});

// Set initial state from active toggle
const activeOpt = Array.from(dom.switchOpts).find(o => o.classList.contains('active'));
if (activeOpt) state.type = activeOpt.dataset.value;

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

function openModal(title, disableBack = false) {
    dom.modalTitle.innerText = title;
    dom.modalList.innerHTML = '';
    dom.finalUrl.style.display = 'none';
    dom.overlay.style.display = 'flex';
    
    // Check if we should show back button
    // We show it if modalHistory is NOT empty AND it hasn't been explicitly disabled
    if (state.modalHistory.length > 0 && !disableBack) {
        dom.modalBackBtn.style.display = 'flex'; // Use flex for better alignment
    } else {
        dom.modalBackBtn.style.display = 'none';
    }
}

function closeModal() {
    state.modalHistory = [];
    dom.overlay.style.display = 'none';
}

dom.modalBackBtn.onclick = () => {
    if (state.modalHistory.length > 0) {
        const prevView = state.modalHistory.pop();
        prevView();
    }
};

dom.closeModal.onclick = closeModal;

dom.overlay.onclick = (e) => {
    if (e.target === dom.overlay) closeModal();
};

// --- Drawer Logic ---

function openDrawer() {
    renderFavorites();
    dom.drawer.classList.add('active');
    dom.drawerOverlay.classList.add('active');
}

function closeDrawer() {
    dom.drawer.classList.remove('active');
    dom.drawerOverlay.classList.remove('active');
}

dom.favoritesBtn.onclick = openDrawer;
dom.closeDrawer.onclick = closeDrawer;
dom.drawerOverlay.onclick = closeDrawer;

// --- Rendering Logic ---

function renderResults(results, type) {
    dom.resultsGrid.innerHTML = '';
    
    if (!results || results.length === 0) {
        dom.resultsGrid.innerHTML = '<p style="text-align:center; grid-column: 1/-1; color: var(--text-secondary); padding: 2rem;">No results found.</p>';
        return;
    }

    results.forEach(item => {
        const isFav = state.favorites.some(f => f.url === item.url);
        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-header">
                <span class="type-badge">${type}</span>
                <button class="fav-toggle ${isFav ? 'active' : ''}" title="${isFav ? 'Remove from Favorites' : 'Add to Favorites'}">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                </button>
            </div>
            <h3>${item.name}</h3>
        `;
        
        const favBtn = div.querySelector('.fav-toggle');
        favBtn.onclick = (e) => {
            e.stopPropagation();
            toggleFavorite(item, type);
        };

        div.onclick = () => {
             state.modalHistory = [];
             handleItemClick(item, type);
        };
        dom.resultsGrid.appendChild(div);
    });
}

function toggleFavorite(item, type) {
    const idx = state.favorites.findIndex(f => f.url === item.url);
    if (idx >= 0) {
        state.favorites.splice(idx, 1);
    } else {
        state.favorites.push({ ...item, type });
    }
    localStorage.setItem('vortexFavorites', JSON.stringify(state.favorites));
    
    // Refresh both views if they are visible
    renderResults(state.results, state.type);
    if (dom.drawer.classList.contains('active')) {
        renderFavorites();
    }
}

function renderFavorites() {
    dom.favoritesList.innerHTML = '';
    
    if (state.favorites.length === 0) {
        dom.favoritesList.innerHTML = '<div class="drawer-empty">Your favorites list is empty.</div>';
        return;
    }
    
    state.favorites.forEach(item => {
        const div = document.createElement('div');
        div.className = 'drawer-item';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <span class="type-badge">${item.type}</span>
                <button class="fav-toggle active" style="padding: 0; color: var(--danger);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                </button>
            </div>
            <h4>${item.name}</h4>
        `;
        
        const favBtn = div.querySelector('.fav-toggle');
        favBtn.onclick = (e) => {
            e.stopPropagation();
            toggleFavorite(item, item.type);
        };

        div.onclick = () => {
             closeDrawer();
             state.modalHistory = [];
             handleItemClick(item, item.type);
        };
        dom.favoritesList.appendChild(div);
    });
}

// --- Detail View Logic ---

async function handleItemClick(item, type, isBackAction = false) {
    if (type === 'series') {
        openModal('Select Episode', !isBackAction && state.modalHistory.length === 0);
        showModalLoading(true);
        const data = await apiGetEpisodes(item.url);
        state.currentEpisodes = data.episodes;
        showModalLoading(false);

        const currentViewRenderer = () => handleItemClick(item, type, true);

        // Add Bulk Resolve Section
        const bulkDiv = document.createElement('div');
        bulkDiv.style.marginBottom = '1.5rem';
        bulkDiv.style.padding = '1rem';
        bulkDiv.style.backgroundColor = 'var(--bg-main)';
        bulkDiv.style.borderRadius = 'var(--radius)';
        bulkDiv.style.display = 'flex';
        bulkDiv.style.flexDirection = 'column';
        bulkDiv.style.gap = '0.5rem';
        bulkDiv.style.border = '1px solid var(--border)';

        bulkDiv.innerHTML = `
            <div style="display: flex; gap: 0.5rem; justify-content: space-between; align-items: center;">
                <label style="color: var(--text-secondary); font-size: 0.85rem;">From Ep:</label>
                <input type="number" id="bulkStart" value="1" min="1" max="${state.currentEpisodes.length}" style="width: 60px; padding: 0.25rem; border-radius: var(--radius); border: 1px solid var(--border);">
                <label style="color: var(--text-secondary); font-size: 0.85rem;">To Ep:</label>
                <input type="number" id="bulkEnd" value="${state.currentEpisodes.length}" min="1" max="${state.currentEpisodes.length}" style="width: 60px; padding: 0.25rem; border-radius: var(--radius); border: 1px solid var(--border);">
            </div>
            <button class="btn-primary" id="btnBulkResolve" style="width: 100%; margin-top: 0.5rem;">RESOLVE RANGE</button>
        `;
        dom.modalList.appendChild(bulkDiv);

        document.getElementById('btnBulkResolve').onclick = () => {
            let start = parseInt(document.getElementById('bulkStart').value) || 1;
            let end = parseInt(document.getElementById('bulkEnd').value) || state.currentEpisodes.length;
            if (start > end) [start, end] = [end, start];
            const selected = state.currentEpisodes.slice(start - 1, end);
            state.modalHistory.push(currentViewRenderer);
            handleBulkResolve(selected);
        };

        state.currentEpisodes.forEach((ep, index) => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerText = `${index + 1}. ${ep.name}`;
            row.onclick = () => {
                state.modalHistory.push(currentViewRenderer);
                handleQualitySelect(ep.url);
            }
            dom.modalList.appendChild(row);
        });
    } else {
        // For movies, we want a back button that just closes the modal
        state.modalHistory.push(() => closeModal());
        handleQualitySelect(item.url);
    }
}

async function handleQualitySelect(url, isBackAction = false) {
    // If not a back action and it's a series, we should already have a history item (the episode list)
    // If it's a movie, we pushed a "closeModal" action in handleItemClick
    openModal('Select Quality', !isBackAction && state.modalHistory.length === 0);
    showModalLoading(true);
    const data = await apiGetQualities(url);
    showModalLoading(false);
    
    const currentViewRenderer = () => handleQualitySelect(url, true);

    data.qualities.forEach(q => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `
            <span class="quality-tag">${q.quality}</span>
            <span class="size-tag">${q.size}</span>
        `;
        row.onclick = () => {
            state.modalHistory.push(currentViewRenderer);
            resolveFinalUrl(q.link_id);
        }
        dom.modalList.appendChild(row);
    });
}

async function resolveFinalUrl(link_id) {
    openModal('Finalizing Link');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2.5rem;">
            <p style="margin-bottom: 2rem; color: var(--text-secondary);">Preparing your secure direct link...</p>
            <div class="spinner" style="margin: 0 auto;"></div>
        </div>
    `;

    const data = await apiResolve(link_id);
    if (data.url) {
        renderFinalUrlScreen(data.url);
    } else {
        dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center; padding: 2rem;">Error resolving link. Please try another quality.</p>';
    }
}

function renderFinalUrlScreen(url) {
    dom.modalTitle.innerText = "Direct Link";
    dom.modalList.innerHTML = `
        <div class="result-container">
            <p class="result-label">Direct Link:</p>
            <div class="link-display-box">
                <code class="raw-url">${url}</code>
                <button class="btn-secondary btn-sm" id="btnCopySingle">COPY</button>
            </div>
            
            <div style="margin-top: 1.5rem; display: flex; flex-direction: column; gap: 0.75rem;">
                <a href="${url}" class="btn-primary" style="text-align:center; text-decoration:none;" target="_blank">DOWNLOAD VIA BROWSER</a>
                <button class="btn-secondary" style="border-color: #f39c12; color: #f39c12; padding: 0.85rem;" id="btnStream">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none" style="vertical-align: middle; margin-right: 8px;">
                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                    STREAM IN BROWSER
                </button>
            </div>
        </div>
    `;
    
    document.getElementById('btnCopySingle').onclick = (e) => copyLinkToClipboard(url, e.target);
    document.getElementById('btnStream').onclick = () => playVideo(url);
}

function playVideo(url) {
    state.modalHistory.push(() => renderFinalUrlScreen(url));
    dom.modalTitle.innerText = "Playing Video";
    dom.modalList.innerHTML = `
        <div style="padding: 1rem; width: 100%; display: flex; flex-direction: column; background: #000; border-radius: var(--radius); overflow: hidden;">
            <video controls autoplay playsinline style="width: 100%; height: auto; outline: none; background: #000; border-radius: var(--radius); object-fit: contain;">
                <source src="${url}" type="video/mp4">
                Your browser does not support HTML5 video.
            </video>
        </div>
    `;
}

async function handleBulkResolve(episodesToResolve) {
    if (!episodesToResolve || episodesToResolve.length === 0) return;
    openModal('Bulk Resolving...');
    dom.modalList.innerHTML = `
        <div style="text-align:center; padding: 2.5rem;">
            <p style="margin-bottom: 2rem; color: var(--text-secondary);">Processing ${episodesToResolve.length} items in parallel...</p>
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
                <p style="margin-bottom: 1rem; color: var(--text-secondary);">Successfully resolved ${data.results.length} links.</p>
                <textarea class="links-box" readonly>${linksText}</textarea>
                <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                    <button class="btn-primary" style="flex: 1;" id="btnCopyBulk">COPY ALL</button>
                    <a href="${downloadUrl}" download="links.txt" class="btn-secondary" style="flex: 1; text-align: center; text-decoration: none; padding: 0.75rem 1rem;">DOWNLOAD TXT</a>
                </div>
            `;
            
            document.getElementById('btnCopyBulk').onclick = (e) => {
                const textarea = dom.modalList.querySelector('.links-box');
                textarea.select();
                document.execCommand('copy');
                const btn = e.target;
                const originalText = btn.innerText;
                btn.innerText = 'COPIED!';
                setTimeout(() => btn.innerText = originalText, 2000);
            };
        } else {
            dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center;">Failed to resolve links.</p>';
        }
    } catch (e) {
        dom.modalList.innerHTML = '<p style="color:var(--danger); text-align:center;">An error occurred.</p>';
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

// --- Search Event Handlers ---

async function doSearch() {
    const q = dom.searchInput.value.trim();
    const type = state.type; // Use state variable updated by switch
    if (!q) return;

    showLoading(true);
    dom.resultsGrid.innerHTML = '';
    state.results = [];

    try {
        const data = await apiSearch(q, type);
        state.results = data.results || [];
        renderResults(state.results, type);
    } catch (e) {
        console.error(e);
        alert('Error searching. Please try again.');
    } finally {
        showLoading(false);
    }
}

dom.searchBtn.onclick = doSearch;

dom.searchInput.onkeypress = (e) => {
    if (e.key === 'Enter') doSearch();
};
