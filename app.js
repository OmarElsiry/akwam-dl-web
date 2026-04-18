// ============================================================
//  State
// ============================================================
const state = {
    results:       [],
    type:          'movie',   // Akwam type filter
    provider:      'akwam',   // 'akwam' | 'egydead'
    currentUrl:    '',
    currentEpisodes: [],
    favorites:     [],
    modalHistory:  [],
    storageKey:    'vortexFavorites'
};

// ============================================================
//  DOM References
// ============================================================
const dom = {
    searchBtn:       document.getElementById('searchBtn'),
    searchInput:     document.getElementById('searchInput'),
    resultsGrid:     document.getElementById('resultsGrid'),
    loading:         document.getElementById('loading'),
    overlay:         document.getElementById('overlay'),
    mainModal:       document.getElementById('mainModal'),
    modalTitle:      document.getElementById('modalTitle'),
    modalList:       document.getElementById('modalList'),
    modalLoading:    document.getElementById('modalLoading'),
    closeModal:      document.getElementById('closeModal'),
    modalBackBtn:    document.getElementById('modalBackBtn'),
    finalUrl:        document.getElementById('finalUrl'),
    favoritesBtn:    document.getElementById('favoritesBtn'),
    typeWrapper:     document.getElementById('typeWrapper'),
    searchTypeSwitch:document.getElementById('searchTypeSwitch'),
    switchOpts:      document.querySelectorAll('.switch-opt'),
    providerSwitch:  document.getElementById('providerSwitch'),
    providerOpts:    document.querySelectorAll('.provider-opt'),
    drawer:          document.getElementById('drawer'),
    drawerOverlay:   document.getElementById('drawerOverlay'),
    favoritesList:   document.getElementById('favoritesList'),
    closeDrawer:     document.getElementById('closeDrawer'),
    donateBtn:       document.getElementById('donateBtn'),
    donationOverlay: document.getElementById('donationOverlay'),
    closeDonation:   document.getElementById('closeDonation'),
    brandName:       document.getElementById('brandName'),
    pageTitle:       document.getElementById('pageTitle')
};

// ============================================================
//  Branding
// ============================================================
function updateBranding() {
    const host = window.location.hostname;
    let name = 'Vortex';
    if (host.includes('lazyus')) name = 'Lazyus';
    else if (host.includes('zilos')) name = 'Zilos';
    if (dom.brandName) dom.brandName.innerText = name;
    if (dom.pageTitle) dom.pageTitle.innerText = `${name} Premium`;
    state.storageKey = `${name.toLowerCase()}Favorites`;
    state.favorites = JSON.parse(localStorage.getItem(state.storageKey)) || [];
}
updateBranding();

// ============================================================
//  Provider Switch
// ============================================================
dom.providerOpts.forEach(opt => {
    opt.onclick = () => {
        dom.providerOpts.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        state.provider = opt.dataset.value;
        state.results = [];
        dom.resultsGrid.innerHTML = '';
        // Show/hide type switch – only Akwam needs movie/series filter
        dom.typeWrapper.style.display = state.provider === 'akwam' ? '' : 'none';
        dom.searchInput.placeholder = state.provider === 'egydead'
            ? 'Search movies, series, episodes…'
            : 'Enter title to search…';
    };
});

// ============================================================
//  Content-Type (Movies / Series) Switch  —  Akwam only
// ============================================================
dom.switchOpts.forEach(opt => {
    opt.onclick = () => {
        dom.switchOpts.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        state.type = opt.dataset.value;
        state.results = [];
        dom.resultsGrid.innerHTML = '';
    };
});
const activeOpt = Array.from(dom.switchOpts).find(o => o.classList.contains('active'));
if (activeOpt) state.type = activeOpt.dataset.value;

// ============================================================
//  API helpers — Akwam
// ============================================================
async function apiSearch(query, type) {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
    return res.json();
}
async function apiGetEpisodes(url) {
    const res = await fetch('/api/episodes', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function apiGetQualities(url) {
    const res = await fetch('/api/qualities', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function apiResolve(url) {
    const res = await fetch('/api/resolve', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function apiBulkResolve(urls) {
    const res = await fetch('/api/bulk-resolve', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({urls}) });
    return res.json();
}

// ============================================================
//  API helpers — EgyDead
// ============================================================
async function egyDeadSearch(query) {
    const res = await fetch(`/api/egydead/search?q=${encodeURIComponent(query)}`);
    return res.json();
}
async function egyDeadGetSeasons(url) {
    const res = await fetch('/api/egydead/seasons', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function egyDeadGetEpisodes(url) {
    const res = await fetch('/api/egydead/episodes', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function egyDeadGetWatch(url) {
    const res = await fetch('/api/egydead/watch', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}

// ============================================================
//  Loading helpers
// ============================================================
function showLoading(v)      { dom.loading.style.display = v ? 'flex' : 'none'; }
function showModalLoading(v) { dom.modalLoading.style.display = v ? 'flex' : 'none'; }

// ============================================================
//  Modal helpers
// ============================================================
function openModal(title, showBack = false, wideVideo = false) {
    dom.modalTitle.innerText = title;
    dom.modalList.innerHTML  = '';
    dom.finalUrl.style.display = 'none';
    dom.overlay.style.display  = 'flex';
    dom.modalBackBtn.style.display = showBack ? 'flex' : 'none';
    // Wide mode for video embeds
    if (wideVideo) dom.mainModal.classList.add('modal-wide');
    else           dom.mainModal.classList.remove('modal-wide');
}

function closeModal() {
    state.modalHistory = [];
    dom.overlay.style.display = 'none';
    dom.mainModal.classList.remove('modal-wide');
}

dom.modalBackBtn.onclick = () => {
    if (state.modalHistory.length > 0) {
        const prev = state.modalHistory.pop();
        prev();
    }
};
dom.closeModal.onclick = closeModal;

// Donation modal
if (dom.donateBtn)     dom.donateBtn.onclick    = () => dom.donationOverlay.classList.add('active');
if (dom.closeDonation) dom.closeDonation.onclick = () => dom.donationOverlay.classList.remove('active');

// Click-outside to close
window.addEventListener('click', e => {
    if (e.target === dom.overlay)         closeModal();
    if (e.target === dom.drawerOverlay)   closeDrawer();
    if (e.target === dom.donationOverlay) dom.donationOverlay.classList.remove('active');
});

// Clipboard
window.copyToClipboard = async (text, btn) => {
    try {
        await navigator.clipboard.writeText(text);
        const orig = btn.innerText;
        btn.innerText = 'COPIED!'; btn.classList.add('btn-success');
        setTimeout(() => { btn.innerText = orig; btn.classList.remove('btn-success'); }, 2000);
    } catch (err) { console.error('Clipboard error', err); }
};

// ============================================================
//  Favorites Drawer
// ============================================================
function openDrawer()  { renderFavorites(); dom.drawer.classList.add('active'); dom.drawerOverlay.classList.add('active'); }
function closeDrawer() { dom.drawer.classList.remove('active'); dom.drawerOverlay.classList.remove('active'); }

dom.favoritesBtn.onclick = openDrawer;
dom.closeDrawer.onclick  = closeDrawer;
dom.drawerOverlay.onclick = closeDrawer;

function toggleFavorite(item, type) {
    const idx = state.favorites.findIndex(f => f.url === item.url);
    if (idx >= 0) state.favorites.splice(idx, 1);
    else           state.favorites.push({ ...item, type });
    localStorage.setItem(state.storageKey, JSON.stringify(state.favorites));
    renderResults(state.results, type === 'movie' ? 'movie' : type);
    if (dom.drawer.classList.contains('active')) renderFavorites();
}

// ============================================================
//  Results Grid
// ============================================================
function renderResults(results, type) {
    dom.resultsGrid.innerHTML = '';
    if (!results || results.length === 0) {
        dom.resultsGrid.innerHTML = '<p style="text-align:center;grid-column:1/-1;color:var(--text-secondary);padding:2rem;">No results found.</p>';
        return;
    }

    results.forEach(item => {
        const isFav = state.favorites.some(f => f.url === item.url);
        const isEgyDead = item.source === 'egydead';
        const badgeText = isEgyDead ? (item.type || 'movie') : type;
        const badgeClass = isEgyDead ? 'type-badge badge-egydead' : 'type-badge';
        const sourceTag = isEgyDead
            ? '<span class="source-badge source-egydead">EgyDead</span>'
            : '<span class="source-badge source-akwam">Akwam</span>';

        const div = document.createElement('div');
        div.className = 'result-item';
        div.innerHTML = `
            <div class="result-header">
                <div style="display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">
                    ${sourceTag}
                    <span class="${badgeClass}">${badgeText}</span>
                </div>
                <button class="fav-toggle ${isFav ? 'active' : ''}" title="${isFav ? 'Remove from Favorites' : 'Add to Favorites'}">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                </button>
            </div>
            <h3>${item.name}</h3>
        `;
        div.querySelector('.fav-toggle').onclick = e => { e.stopPropagation(); toggleFavorite(item, badgeText); };
        div.onclick = () => { state.modalHistory = []; handleItemClick(item, badgeText); };
        dom.resultsGrid.appendChild(div);
    });
}

function renderFavorites() {
    dom.favoritesList.innerHTML = '';
    if (state.favorites.length === 0) {
        dom.favoritesList.innerHTML = '<div class="drawer-empty">Your favorites list is empty.</div>';
        return;
    }
    state.favorites.forEach(item => {
        const isEgyDead = item.source === 'egydead';
        const sourceTag = isEgyDead
            ? '<span class="source-badge source-egydead">EgyDead</span>'
            : '<span class="source-badge source-akwam">Akwam</span>';
        const div = document.createElement('div');
        div.className = 'drawer-item';
        div.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="display:flex;gap:0.4rem;">${sourceTag}<span class="type-badge">${item.type}</span></div>
                <button class="fav-toggle active" style="padding:0;color:var(--danger);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
                </button>
            </div>
            <h4>${item.name}</h4>
        `;
        div.querySelector('.fav-toggle').onclick = e => { e.stopPropagation(); toggleFavorite(item, item.type); };
        div.onclick = () => { closeDrawer(); state.modalHistory = []; handleItemClick(item, item.type); };
        dom.favoritesList.appendChild(div);
    });
}

// ============================================================
//  Unified click dispatcher
// ============================================================
function handleItemClick(item, type) {
    if (item.source === 'egydead') {
        handleEgyDeadClick(item);
    } else {
        handleAkwamClick(item, type);
    }
}

// ============================================================
//  AKWAM flow  (unchanged logic, just renamed for clarity)
// ============================================================
async function handleAkwamClick(item, type, isBackAction = false) {
    if (type === 'series') {
        openModal('Select Episode', !isBackAction && state.modalHistory.length === 0);
        showModalLoading(true);
        const data = await apiGetEpisodes(item.url);
        state.currentEpisodes = data.episodes || [];
        showModalLoading(false);

        const currentViewRenderer = () => handleAkwamClick(item, type, true);

        const bulkDiv = document.createElement('div');
        bulkDiv.style.cssText = 'margin-bottom:1.5rem;padding:1rem;background:var(--bg-main);border-radius:var(--radius);display:flex;flex-direction:column;gap:0.5rem;border:1px solid var(--border);';
        bulkDiv.innerHTML = `
            <div style="display:flex;gap:0.5rem;justify-content:space-between;align-items:center;">
                <label style="color:var(--text-secondary);font-size:0.85rem;">From Ep:</label>
                <input type="number" id="bulkStart" value="1" min="1" max="${state.currentEpisodes.length}" style="width:60px;padding:0.25rem;border-radius:var(--radius);border:1px solid var(--border);">
                <label style="color:var(--text-secondary);font-size:0.85rem;">To Ep:</label>
                <input type="number" id="bulkEnd" value="${state.currentEpisodes.length}" min="1" max="${state.currentEpisodes.length}" style="width:60px;padding:0.25rem;border-radius:var(--radius);border:1px solid var(--border);">
            </div>
            <button class="btn-primary" id="btnBulkResolve" style="width:100%;margin-top:0.5rem;">RESOLVE RANGE</button>
        `;
        dom.modalList.appendChild(bulkDiv);

        document.getElementById('btnBulkResolve').onclick = () => {
            let start = parseInt(document.getElementById('bulkStart').value) || 1;
            let end   = parseInt(document.getElementById('bulkEnd').value)   || state.currentEpisodes.length;
            if (start > end) [start, end] = [end, start];
            const selected = state.currentEpisodes.slice(start - 1, end);
            state.modalHistory.push(currentViewRenderer);
            handleBulkResolve(selected);
        };

        state.currentEpisodes.forEach((ep, index) => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerText = `${index + 1}. ${ep.name}`;
            row.onclick = () => { state.modalHistory.push(currentViewRenderer); handleQualitySelect(ep.url); };
            dom.modalList.appendChild(row);
        });
    } else {
        state.modalHistory.push(() => closeModal());
        handleQualitySelect(item.url);
    }
}

async function handleQualitySelect(url) {
    openModal('Select Quality', true);
    showModalLoading(true);
    const data = await apiGetQualities(url);
    showModalLoading(false);
    const currentViewRenderer = () => handleQualitySelect(url);

    data.qualities.forEach(q => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span class="quality-tag">${q.quality}</span><span class="size-tag">${q.size}</span>`;
        row.onclick = () => { state.modalHistory.push(currentViewRenderer); resolveFinalUrl(q.link_id); };
        dom.modalList.appendChild(row);
    });
}

async function resolveFinalUrl(link_id) {
    openModal('Finalizing Link');
    dom.modalList.innerHTML = `
        <div style="text-align:center;padding:2.5rem;">
            <p style="margin-bottom:2rem;color:var(--text-secondary);">Preparing your secure direct link...</p>
            <div class="spinner" style="margin:0 auto;"></div>
        </div>`;
    const data = await apiResolve(link_id);
    if (data.url) renderFinalUrlScreen(data.url);
    else dom.modalList.innerHTML = '<p style="color:var(--danger);text-align:center;padding:2rem;">Error resolving link. Try another quality.</p>';
}

function renderFinalUrlScreen(url) {
    dom.modalTitle.innerText = 'Direct Link';
    dom.modalList.innerHTML = `
        <div class="result-container">
            <p class="result-label">Direct Link:</p>
            <div class="link-display-box">
                <code class="raw-url">${url}</code>
                <button class="btn-secondary btn-sm" id="btnCopySingle">COPY</button>
            </div>
            <div style="margin-top:1.5rem;display:flex;flex-direction:column;gap:0.75rem;">
                <a href="${url}" class="btn-primary" style="text-align:center;text-decoration:none;" target="_blank">DOWNLOAD VIA BROWSER</a>
                <button class="btn-secondary" style="border-color:#f39c12;color:#f39c12;padding:0.85rem;" id="btnStream">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:8px;"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                    STREAM IN BROWSER
                </button>
            </div>
        </div>`;
    document.getElementById('btnCopySingle').onclick = e => copyLinkToClipboard(url, e.target);
    document.getElementById('btnStream').onclick = () => playVideo(url);
}

function playVideo(url) {
    state.modalHistory.push(() => renderFinalUrlScreen(url));
    dom.modalTitle.innerText = 'Playing Video';
    dom.modalList.innerHTML = `
        <div style="padding:1rem;width:100%;display:flex;flex-direction:column;background:#000;border-radius:var(--radius);overflow:hidden;">
            <video controls autoplay playsinline style="width:100%;height:auto;outline:none;background:#000;border-radius:var(--radius);object-fit:contain;">
                <source src="${url}" type="video/mp4">
                Your browser does not support HTML5 video.
            </video>
        </div>`;
}

async function handleBulkResolve(episodesToResolve) {
    if (!episodesToResolve || episodesToResolve.length === 0) return;
    openModal('Bulk Resolving...');
    dom.modalList.innerHTML = `<div style="text-align:center;padding:2.5rem;"><p style="margin-bottom:2rem;color:var(--text-secondary);">Processing ${episodesToResolve.length} items in parallel...</p><div class="spinner" style="margin:0 auto;"></div></div>`;
    try {
        const data = await apiBulkResolve(episodesToResolve);
        if (data.results && data.results.length > 0) {
            const linksText = data.results.map(r => r.url).join('\n');
            const blob = new Blob([linksText], { type: 'text/plain' });
            const downloadUrl = URL.createObjectURL(blob);
            dom.modalList.innerHTML = `
                <p style="margin-bottom:1rem;color:var(--text-secondary);">Successfully resolved ${data.results.length} links.</p>
                <textarea class="links-box" readonly>${linksText}</textarea>
                <div style="display:flex;gap:0.5rem;margin-top:1rem;">
                    <button class="btn-primary" style="flex:1;" id="btnCopyBulk">COPY ALL</button>
                    <a href="${downloadUrl}" download="links.txt" class="btn-secondary" style="flex:1;text-align:center;text-decoration:none;padding:0.75rem 1rem;">DOWNLOAD TXT</a>
                </div>`;
            document.getElementById('btnCopyBulk').onclick = e => {
                dom.modalList.querySelector('.links-box').select();
                document.execCommand('copy');
                const btn = e.target;
                const orig = btn.innerText; btn.innerText = 'COPIED!';
                setTimeout(() => btn.innerText = orig, 2000);
            };
        } else {
            dom.modalList.innerHTML = '<p style="color:var(--danger);text-align:center;">Failed to resolve links.</p>';
        }
    } catch (e) {
        dom.modalList.innerHTML = '<p style="color:var(--danger);text-align:center;">An error occurred.</p>';
    }
}

async function copyLinkToClipboard(text, btn) {
    try {
        await navigator.clipboard.writeText(text);
        const orig = btn.innerText;
        btn.innerText = 'COPIED!'; btn.classList.add('btn-success');
        setTimeout(() => { btn.innerText = orig; btn.classList.remove('btn-success'); }, 2000);
    } catch (err) { console.error('Clipboard error', err); }
}

// ============================================================
//  EGYDEAD flow
// ============================================================
async function handleEgyDeadClick(item) {
    state.modalHistory = [];
    switch (item.type) {
        case 'movie':
        case 'episode':
            await egyDeadShowWatch(item);
            break;
        case 'series':
        case 'collection':
            await egyDeadShowSeasons(item);
            break;
        case 'season':
            await egyDeadShowEpisodes(item);
            break;
        default:
            await egyDeadShowWatch(item);
    }
}

async function egyDeadShowSeasons(item) {
    openModal(`${item.name}`, false);
    showModalLoading(true);
    const data = await egyDeadGetSeasons(item.url);
    showModalLoading(false);

    const seasons = data.seasons || [];
    if (seasons.length === 0) {
        // No seasons page – treat as direct watchable
        await egyDeadShowWatch(item);
        return;
    }

    const currentViewRenderer = () => egyDeadShowSeasons(item);
    dom.modalTitle.innerText = `${item.name} — Seasons`;

    seasons.forEach(season => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${season.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.modalHistory.push(currentViewRenderer);
            egyDeadShowEpisodes(season);
        };
        dom.modalList.appendChild(row);
    });
}

async function egyDeadShowEpisodes(item) {
    openModal(`${item.name}`, state.modalHistory.length > 0);
    showModalLoading(true);
    const data = await egyDeadGetEpisodes(item.url);
    showModalLoading(false);

    const episodes = data.episodes || [];
    dom.modalTitle.innerText = `${item.name} — Episodes`;

    if (episodes.length === 0) {
        dom.modalList.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:2rem;">No episodes found.</p>';
        return;
    }

    const currentViewRenderer = () => egyDeadShowEpisodes(item);

    episodes.forEach((ep, idx) => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${idx + 1}. ${ep.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.modalHistory.push(currentViewRenderer);
            egyDeadShowWatch(ep);
        };
        dom.modalList.appendChild(row);
    });
}

async function egyDeadShowWatch(item) {
    openModal(`Loading…`, state.modalHistory.length > 0, false);
    showModalLoading(true);
    const data = await egyDeadGetWatch(item.url);
    showModalLoading(false);
    egyDeadRenderWatch(data, item);
}

function egyDeadRenderWatch(data, item) {
    const embedUrls  = data.embed_urls  || [];
    const directUrls = data.direct_urls || [];

    // ── Case 1: we have an embed iframe ──────────────────────
    if (embedUrls.length > 0) {
        dom.mainModal.classList.add('modal-wide');
        dom.modalTitle.innerText = item.name;

        let serverBtns = '';
        if (embedUrls.length > 1) {
            serverBtns = embedUrls.map((u, i) =>
                `<button class="server-btn ${i === 0 ? 'active' : ''}" data-src="${u}" onclick="egyDeadSwitchServer(this)">Server ${i + 1}</button>`
            ).join('');
        }

        dom.modalList.innerHTML = `
            <div class="watch-container">
                ${serverBtns ? `<div class="server-row">${serverBtns}</div>` : ''}
                <div class="embed-frame-wrap">
                    <iframe id="egyDeadFrame" src="${embedUrls[0]}"
                        frameborder="0" allowfullscreen allow="autoplay; fullscreen"
                        sandbox="allow-scripts allow-same-origin allow-forms allow-popups">
                    </iframe>
                </div>
                <a href="${item.url}" target="_blank" class="btn-secondary btn-open-page">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    Open in EgyDead
                </a>
            </div>`;
        return;
    }

    // ── Case 2: direct mp4/m3u8 ──────────────────────────────
    if (directUrls.length > 0) {
        renderFinalUrlScreen(directUrls[0]);
        return;
    }

    // ── Case 3: nothing found, offer link to page ─────────────
    dom.modalTitle.innerText = 'Watch';
    dom.modalList.innerHTML = `
        <div style="text-align:center;padding:2rem;">
            <p style="color:var(--text-secondary);margin-bottom:1.5rem;">
                Could not extract a direct stream. Open the page in your browser to watch.
            </p>
            <a href="${item.url}" target="_blank" class="btn-primary" style="display:inline-block;text-decoration:none;">
                OPEN IN EGYDEAD
            </a>
        </div>`;
}

// Switch embed server
window.egyDeadSwitchServer = btn => {
    document.querySelectorAll('.server-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const frame = document.getElementById('egyDeadFrame');
    if (frame) frame.src = btn.dataset.src;
};

// ============================================================
//  Search dispatcher
// ============================================================
async function doSearch() {
    const q = dom.searchInput.value.trim();
    if (!q) return;

    showLoading(true);
    dom.resultsGrid.innerHTML = '';
    state.results = [];

    try {
        if (state.provider === 'egydead') {
            const data = await egyDeadSearch(q);
            state.results = data.results || [];
            renderResults(state.results, 'egydead');
        } else {
            const data = await apiSearch(q, state.type);
            state.results = data.results || [];
            renderResults(state.results, state.type);
        }
    } catch (e) {
        console.error(e);
        dom.resultsGrid.innerHTML = '<p style="text-align:center;grid-column:1/-1;color:var(--danger);padding:2rem;">Search failed. Please retry.</p>';
    } finally {
        showLoading(false);
    }
}

dom.searchBtn.onclick = doSearch;
dom.searchInput.onkeypress = e => { if (e.key === 'Enter') doSearch(); };
