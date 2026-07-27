// ============================================================
//  State
// ============================================================
const state = {
    results:       [],
    type:          'movie',   // Akwam type filter
    provider:      'akwam',   // 'akwam' | 'egydead' | 'wecima' | 'faselhd' | 'sahid4u'
    currentUrl:    '',
    currentEpisodes: [],
    favorites:     [],
    modalHistory:  [],
    storageKey:    'vortexFavorites',
    activeItem:    null,      // Track currently active item for sharing
    lastFocus:     null
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
    shareModalBtn:   document.getElementById('shareModalBtn'),
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
    shareFavoritesBtn:document.getElementById('shareFavoritesBtn'),
    donateBtn:       document.getElementById('donateBtn'),
    donationOverlay: document.getElementById('donationOverlay'),
    closeDonation:   document.getElementById('closeDonation'),
    brandName:       document.getElementById('brandName'),
    pageTitle:       document.getElementById('pageTitle'),
    toastContainer:  document.getElementById('toastContainer')
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

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    })[char]);
}

function safeRemoteUrl(value) {
    try {
        const url = new URL(value, window.location.origin);
        return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch (_) {
        return '';
    }
}

function playableServers(servers) {
    return (servers || []).map((server, index) => ({
        name: String(server.name || `Server ${index + 1}`),
        url: safeRemoteUrl(server.embed_url || server.url),
    })).filter(server => server.url);
}

function renderPlayerFrame(id, url, title, fallback = '') {
    return `<div class="embed-frame-wrap">
        <div class="embed-frame-stage">
            <iframe id="${escapeHtml(id)}" src="${escapeHtml(url)}" title="${escapeHtml(title)}"
                sandbox="allow-scripts allow-same-origin allow-presentation"
                allow="autoplay; fullscreen; picture-in-picture" allowfullscreen referrerpolicy="origin"></iframe>
        </div>
        <div class="player-resolve-tools" style="display:flex;align-items:center;justify-content:center;gap:.65rem;flex-wrap:wrap;padding:.65rem;">
            <button type="button" class="btn-secondary btn-sm player-resolve-btn"
                data-frame-id="${escapeHtml(id)}" data-src="${escapeHtml(url)}"
                onclick="window.vortexResolvePlayerStream(this)">PLAY DIRECT</button>
            <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"
                class="btn-secondary btn-sm player-open-link" style="text-decoration:none;">OPEN HOST</a>
            <span class="player-resolve-status" role="status" style="color:var(--text-secondary);font-size:.78rem;"></span>
        </div>
        ${fallback}
    </div>`;
}

function teardownPlayerVideo(video) {
    if (!video) return;
    video._tearingDown = true;
    clearTimeout(video._playbackTimer);
    video._playbackTimer = null;
    if (video._hls) {
        try { video._hls.destroy(); } catch (_) { /* Best-effort player cleanup. */ }
        video._hls = null;
    }
    try { video.pause(); } catch (_) { /* Detached media can reject pause. */ }
    video.removeAttribute('src');
    video.querySelectorAll('source').forEach(source => source.removeAttribute('src'));
}

function teardownPlayerContent(root = dom.mainModal) {
    if (!root) return;
    root.querySelectorAll('.embed-frame-wrap').forEach(wrap => {
        if (wrap._resolveController) wrap._resolveController.abort();
        wrap._resolveController = null;
    });
    root.querySelectorAll('video').forEach(teardownPlayerVideo);
    root.querySelectorAll('iframe').forEach(frame => { frame.src = 'about:blank'; });
}

function switchPlayerServer(btn, frameId) {
    const src = safeRemoteUrl(btn.dataset.src);
    if (!src) return;
    const row = btn.closest('.server-row');
    row?.querySelectorAll('.server-btn, .server-btn-wrap').forEach(element => element.classList.remove('active'));
    (btn.closest('.server-btn-wrap') || btn).classList.add('active');
    const frame = document.getElementById(frameId);
    if (frame) {
        const directVideo = frame.parentElement?.querySelector('video.player-direct-video');
        if (directVideo) {
            teardownPlayerVideo(directVideo);
            directVideo.remove();
        }
        frame.style.display = '';
        frame.src = src;
        const wrap = frame.closest('.embed-frame-wrap');
        if (wrap?._resolveController) wrap._resolveController.abort();
        if (wrap) wrap._resolveController = null;
        const resolveBtn = wrap?.querySelector('.player-resolve-btn');
        const openLink = wrap?.querySelector('.player-open-link');
        const status = wrap?.querySelector('.player-resolve-status');
        if (resolveBtn) {
            resolveBtn.dataset.src = src;
            resolveBtn.disabled = false;
        }
        if (openLink) openLink.href = src;
        if (status) status.textContent = '';
    }
}

let hlsLibraryPromise = null;

function loadHlsLibrary() {
    if (window.Hls) return Promise.resolve(window.Hls);
    if (hlsLibraryPromise) return hlsLibraryPromise;
    hlsLibraryPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/hls.js@1.6.13/dist/hls.min.js';
        script.async = true;
        const timeout = setTimeout(() => {
            script.remove();
            reject(new Error('HLS playback support timed out'));
        }, 10000);
        script.onload = () => {
            clearTimeout(timeout);
            window.Hls ? resolve(window.Hls) : reject(new Error('HLS library unavailable'));
        };
        script.onerror = () => {
            clearTimeout(timeout);
            reject(new Error('Could not load HLS playback support'));
        };
        document.head.appendChild(script);
    }).catch(error => {
        hlsLibraryPromise = null;
        throw error;
    });
    return hlsLibraryPromise;
}

window.vortexResolvePlayerStream = async function(button) {
    const embedUrl = safeRemoteUrl(button.dataset.src);
    const frameId = button.dataset.frameId;
    const frame = document.getElementById(frameId);
    const wrap = frame?.closest('.embed-frame-wrap');
    const status = wrap?.querySelector('.player-resolve-status');
    if (!embedUrl || !frame || !wrap) return;

    if (wrap._resolveController) wrap._resolveController.abort();
    const controller = new AbortController();
    wrap._resolveController = controller;
    button.disabled = true;
    if (status) status.textContent = 'Resolving host…';
    let cleanupDirect = null;
    const timeout = setTimeout(() => controller.abort(), 35000);
    try {
        const response = await fetch('/api/resolve-embed', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: embedUrl }),
            signal: controller.signal,
        });
        const data = await response.json();
        if (wrap._resolveController !== controller || button.dataset.src !== embedUrl) return;
        if (!response.ok || !(data.proxy_url || data.url)) {
            throw new Error(data.detail || data.error || 'Host could not be resolved');
        }

        const oldVideo = wrap.querySelector('video.player-direct-video');
        if (oldVideo) {
            teardownPlayerVideo(oldVideo);
            oldVideo.remove();
        }

        const video = document.createElement('video');
        video.className = 'player-direct-video';
        video.controls = true;
        video.autoplay = true;
        video.playsInline = true;
        video.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;background:var(--video-bg);object-fit:contain;';
        frame.style.display = 'none';
        frame.insertAdjacentElement('afterend', video);

        const playbackUrl = data.proxy_url || data.url;
        const isHls = data.ext === 'm3u8' || /(?:m3u8|hls-proxy)/i.test(playbackUrl);
        const fail = message => {
            if (video._tearingDown) return;
            if (status) status.textContent = `${message} — use Open Host.`;
            frame.style.display = '';
            teardownPlayerVideo(video);
            video.remove();
        };
        cleanupDirect = fail;
        if (status) status.textContent = 'Starting playback…';
        video._playbackTimer = setTimeout(() => {
            fail('Direct playback timed out');
        }, 25000);

        video.addEventListener('canplay', () => {
            if (video._tearingDown) return;
            clearTimeout(video._playbackTimer);
            if (status) status.textContent = 'Ready';
            video.play().catch(() => {});
        }, { once: true });
        video.addEventListener('error', () => fail('Direct playback failed'), { once: true });

        if (isHls && !video.canPlayType('application/vnd.apple.mpegurl')) {
            const Hls = await loadHlsLibrary();
            if (wrap._resolveController !== controller || button.dataset.src !== embedUrl) {
                video.remove();
                return;
            }
            if (!Hls.isSupported()) throw new Error('HLS is not supported in this browser');
            const hls = new Hls({ enableWorker: true });
            video._hls = hls;
            hls.on(Hls.Events.ERROR, (_event, detail) => {
                if (detail.fatal) fail('HLS playback failed');
            });
            hls.loadSource(playbackUrl);
            hls.attachMedia(video);
        } else {
            video.src = playbackUrl;
        }
    } catch (error) {
        if (wrap._resolveController !== controller) return;
        const message = error.name === 'AbortError' ? 'Host resolution timed out' : (error.message || 'Direct playback failed');
        if (cleanupDirect) cleanupDirect(message);
        else if (status) status.textContent = `${message} — use Open Host.`;
    } finally {
        clearTimeout(timeout);
        if (wrap._resolveController === controller) {
            wrap._resolveController = null;
            button.disabled = false;
        }
    }
};

function renderEmptyState(kind = 'ready') {
    const states = {
        ready: ['01', 'Ready when you are.', 'Search for a movie or series above. You can switch sources at any time.'],
        empty: ['00', 'Nothing matched that title.', 'Check the spelling or try another source.'],
        error: ['!', 'This source did not respond.', 'Try the search again or choose another source.']
    };
    const [index, title, message] = states[kind] || states.ready;
    dom.resultsGrid.innerHTML = `<div class="empty-state empty-state-${kind}"><span class="empty-index">${index}</span><div><h3>${title}</h3><p>${message}</p></div></div>`;
}

function prepareInteractiveRows(root) {
    root.querySelectorAll('.result-item, .drawer-item, .list-item').forEach(element => {
        if (element.matches('button, a[href]')) return;
        if (element.dataset.keyboardReady) return;
        element.dataset.keyboardReady = 'true';
        element.tabIndex = 0;
        element.setAttribute('role', 'button');
        if (!element.hasAttribute('aria-label')) {
            const label = element.querySelector('h3, h4')?.textContent?.trim();
            if (label) element.setAttribute('aria-label', label);
        }
        element.addEventListener('keydown', event => {
            if (event.target !== element || !['Enter', ' '].includes(event.key)) return;
            event.preventDefault();
            element.click();
        });
    });
}

const interactiveObserver = new MutationObserver(() => {
    prepareInteractiveRows(dom.resultsGrid);
    prepareInteractiveRows(dom.modalList);
    prepareInteractiveRows(dom.favoritesList);
});
[dom.resultsGrid, dom.modalList, dom.favoritesList].forEach(root => {
    interactiveObserver.observe(root, { childList: true, subtree: true });
});
prepareInteractiveRows(document);

// ============================================================
//  Provider Switch
// ============================================================
dom.providerOpts.forEach(opt => {
    opt.onclick = () => {
        dom.providerOpts.forEach(o => {
            o.classList.remove('active');
            o.setAttribute('aria-pressed', 'false');
        });
        opt.classList.add('active');
        opt.setAttribute('aria-pressed', 'true');
        showLoading(false);
        state.provider = opt.dataset.value;
        state.results = [];
        renderEmptyState('ready');
        // Show/hide type switch – only Akwam needs movie/series filter
        dom.typeWrapper.style.display = state.provider === 'akwam' ? '' : 'none';
        if (state.provider === 'egydead') {
            dom.searchInput.placeholder = 'Search movies, series, episodes…';
        } else if (state.provider === 'wecima') {
            dom.searchInput.placeholder = 'Search movies, series, anime…';
        } else if (state.provider === 'faselhd') {
            dom.searchInput.placeholder = 'Search movies, series…';
        } else if (state.provider === 'royaldrama') {
            dom.searchInput.placeholder = 'Search (browse works best — search is limited)…';
            showLoading(true);
            royaldramaHome().then(items => {
                if (state.provider !== 'royaldrama') return;
                state.results = items;
                renderResults(items, 'royaldrama');
                showLoading(false);
            }).catch(() => {
                if (state.provider !== 'royaldrama') return;
                showLoading(false);
                renderEmptyState('error');
            });
        } else if (state.provider === 'sahid4u') {
            dom.searchInput.placeholder = 'Search movies, series…';
        } else {
            dom.searchInput.placeholder = 'Enter title to search…';
        }
    };
});

// ============================================================
//  Content-Type (Movies / Series) Switch  —  Akwam only
// ============================================================
dom.switchOpts.forEach(opt => {
    opt.onclick = () => {
        dom.switchOpts.forEach(o => {
            o.classList.remove('active');
            o.setAttribute('aria-pressed', 'false');
        });
        opt.classList.add('active');
        opt.setAttribute('aria-pressed', 'true');
        state.type = opt.dataset.value;
        state.results = [];
        renderEmptyState('ready');
    };
});
const activeOpt = Array.from(dom.switchOpts).find(o => o.classList.contains('active'));
if (activeOpt) state.type = activeOpt.dataset.value;

// ============================================================
//  API helpers — Akwam  (CLIENT-SIDE via AkwamWorker)
//  All fetching runs in the user's browser, not the server.
// ============================================================
async function apiSearch(query, type) {
    const results = await AkwamWorker.search(query, type);
    return { results };
}
async function apiGetEpisodes(url) {
    const episodes = await AkwamWorker.getEpisodes(url);
    return { episodes };
}
async function apiGetQualities(url) {
    const qualities = await AkwamWorker.getQualities(url);
    return { qualities };
}
async function apiResolve(url) {
    const resolvedUrl = await AkwamWorker.resolveDirectUrl(url);
    return { url: resolvedUrl };
}
async function apiBulkResolve(urls) {
    const results = await AkwamWorker.bulkResolve(urls);
    return { results };
}

// ============================================================
//  API helpers — FaselHD
// ============================================================
async function faselhdSearch(query) {
    const res = await fetch(`/api/faselhd/search?q=${encodeURIComponent(query)}`);
    return res.json();
}
async function faselhdCategories() {
    const res = await fetch('/api/faselhd/categories');
    return res.json();
}
async function faselhdCategoryItems(slug, page) {
    const res = await fetch('/api/faselhd/category', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({slug, page}) });
    return res.json();
}
async function faselhdPostDetail(postId) {
    const res = await fetch(`/api/faselhd/post/${postId}`);
    return res.json();
}
async function faselhdServers(postId) {
    const res = await fetch(`/api/faselhd/servers/${postId}`);
    return res.json();
}
async function faselhdSeries(slug) {
    const res = await fetch(`/api/faselhd/series/${slug}`);
    return res.json();
}
async function faselhdTrending() {
    const res = await fetch('/api/faselhd/trending');
    return res.json();
}

// ============================================================
//  API helpers — Wecima
// ============================================================
async function wecimaSearch(query) {
    const res = await fetch(`/api/wecima/search?q=${encodeURIComponent(query)}`);
    return res.json();
}
async function wecimaDetail(url) {
    const res = await fetch('/api/wecima/detail', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function wecimaSeries(url) {
    const res = await fetch('/api/wecima/series', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({url}) });
    return res.json();
}
async function wecimaEpisodes(postId, season) {
    const res = await fetch('/api/wecima/episodes', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({post_id: String(postId), season}) });
    return res.json();
}
async function wecimaHomepage(tab) {
    const res = await fetch(`/api/wecima/homepage?tab=${tab}`);
    return res.json();
}

// ============================================================
//  API helpers — Sahid4u (hybrid: server API primary, client worker fallback)
// ============================================================
async function sahid4uSearch(query) {
    let serverUnavailable = false;
    try {
        const res = await fetch(`/api/sahid4u/search?q=${encodeURIComponent(query)}`, {
            signal: AbortSignal.timeout(10000),
        });
        if (res.ok) {
            const data = await res.json();
            if (data.results && data.results.length > 0) return data;
        } else serverUnavailable = true;
    } catch (e) {
        serverUnavailable = true;
    }
    const results = await Sahid4uWorker.search(query);
    if (serverUnavailable && results.length === 0) throw new Error('Sahid4u is unavailable');
    return { results };
}
async function sahid4uGetSeasons(url) {
    try {
        const res = await fetch('/api/sahid4u/seasons', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({url}),
            signal: AbortSignal.timeout(10000),
        });
        if (res.ok) {
            const data = await res.json();
            if (data.seasons && data.seasons.length > 0) return data;
        }
    } catch (e) {
        console.warn('[Sahid4u] Server seasons failed, falling back to client worker:', e);
    }
    const seasons = await Sahid4uWorker.getSeasons(url);
    return { seasons };
}
async function sahid4uGetEpisodes(url) {
    try {
        const res = await fetch('/api/sahid4u/episodes', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({url}),
            signal: AbortSignal.timeout(10000),
        });
        if (res.ok) {
            const data = await res.json();
            if (data.episodes && data.episodes.length > 0) return data;
        }
    } catch (e) {
        console.warn('[Sahid4u] Server episodes failed, falling back to client worker:', e);
    }
    const episodes = await Sahid4uWorker.getEpisodes(url);
    return { episodes };
}
async function sahid4uGetWatchDownload(url) {
    try {
        const res = await fetch('/api/sahid4u/watch', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({url}),
            signal: AbortSignal.timeout(10000),
        });
        if (res.ok) {
            const data = await res.json();
            if (data.servers && data.servers.length > 0) return data;
        }
    } catch (e) {
        console.warn('[Sahid4u] Server watch failed, falling back to client worker:', e);
    }
    return await Sahid4uWorker.getContentServersAndDownloads(url);
}
async function sahid4uGetEpisodeSeriesInfo(url) {
    return await Sahid4uWorker.getEpisodeSeriesInfo(url);
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
function showLoading(v) {
    dom.loading.style.display = v ? 'flex' : 'none';
    dom.resultsGrid.setAttribute('aria-busy', String(v));
    dom.searchBtn.disabled = v;
    dom.searchBtn.textContent = v ? 'Searching…' : 'Search';
}
function showModalLoading(v) { dom.modalLoading.style.display = v ? 'flex' : 'none'; }

// ============================================================
//  Modal helpers
// ============================================================
function openModal(title, showBack = false, wideVideo = false) {
    if (dom.overlay.style.display !== 'flex') state.lastFocus = document.activeElement;
    teardownPlayerContent(dom.modalList);
    dom.modalTitle.innerText = title;
    dom.modalList.innerHTML  = '';
    dom.finalUrl.style.display = 'none';
    dom.overlay.style.display  = 'flex';
    dom.overlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('is-locked');
    dom.modalBackBtn.style.display = showBack ? 'flex' : 'none';
    dom.shareModalBtn.style.display = state.activeItem ? 'flex' : 'none';
    // Wide mode for video embeds
    if (wideVideo) dom.mainModal.classList.add('modal-wide');
    else           dom.mainModal.classList.remove('modal-wide');
    requestAnimationFrame(() => dom.closeModal.focus());
}

function closeModal() {
    state.modalHistory = [];
    state.activeItem = null;
    dom.shareModalBtn.style.display = 'none';
    teardownPlayerContent(dom.mainModal);
    dom.overlay.style.display = 'none';
    dom.overlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('is-locked');
    dom.mainModal.classList.remove('modal-wide');
    if (state.lastFocus?.focus) state.lastFocus.focus();
    state.lastFocus = null;
}

dom.modalBackBtn.onclick = () => {
    if (state.modalHistory.length > 0) {
        const prev = state.modalHistory.pop();
        teardownPlayerContent(dom.modalList);
        prev();
    }
};
dom.closeModal.onclick = closeModal;

function openDonation() {
    state.lastFocus = document.activeElement;
    dom.donationOverlay.classList.add('active');
    dom.donationOverlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('is-locked');
    requestAnimationFrame(() => dom.closeDonation.focus());
}

function closeDonation() {
    dom.donationOverlay.classList.remove('active');
    dom.donationOverlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('is-locked');
    if (state.lastFocus?.focus) state.lastFocus.focus();
    state.lastFocus = null;
}

if (dom.donateBtn)     dom.donateBtn.onclick = openDonation;
if (dom.closeDonation) dom.closeDonation.onclick = closeDonation;

// Click-outside to close
window.addEventListener('click', e => {
    if (e.target === dom.overlay)         closeModal();
    if (e.target === dom.drawerOverlay)   closeDrawer();
    if (e.target === dom.donationOverlay) closeDonation();
});

document.addEventListener('keydown', event => {
    const donationOpen = dom.donationOverlay.classList.contains('active');
    const drawerOpen = dom.drawer.classList.contains('active');
    const modalOpen = dom.overlay.style.display === 'flex';

    if (event.key === 'Escape') {
        if (donationOpen) closeDonation();
        else if (drawerOpen) closeDrawer();
        else if (modalOpen) closeModal();
        return;
    }

    if (event.key !== 'Tab') return;
    const panel = donationOpen ? dom.donationOverlay.querySelector('.modal')
        : drawerOpen ? dom.drawer
        : modalOpen ? dom.mainModal
        : null;
    if (!panel) return;

    const focusable = Array.from(panel.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), a[href], [tabindex="0"]'))
        .filter(element => element.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
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
function openDrawer() {
    state.lastFocus = document.activeElement;
    renderFavorites();
    dom.drawer.classList.add('active');
    dom.drawerOverlay.classList.add('active');
    dom.drawer.inert = false;
    dom.drawer.setAttribute('aria-hidden', 'false');
    dom.drawerOverlay.setAttribute('aria-hidden', 'false');
    dom.favoritesBtn.setAttribute('aria-expanded', 'true');
    document.body.classList.add('is-locked');
    requestAnimationFrame(() => dom.closeDrawer.focus());
}
function closeDrawer() {
    dom.drawer.classList.remove('active');
    dom.drawerOverlay.classList.remove('active');
    dom.drawer.inert = true;
    dom.drawer.setAttribute('aria-hidden', 'true');
    dom.drawerOverlay.setAttribute('aria-hidden', 'true');
    dom.favoritesBtn.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('is-locked');
    if (state.lastFocus?.focus) state.lastFocus.focus();
    state.lastFocus = null;
}

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
        renderEmptyState('empty');
        return;
    }

    const seen = new Set();
    const uniqueResults = results.filter(item => {
        const key = item.url || `${item.source || type}:${item.name || ''}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });

    uniqueResults.forEach(item => {
        const isFav = state.favorites.some(f => f.url === item.url);
        const isEgyDead = item.source === 'egydead';
        const isWecima = item.source === 'wecima';
        const isFaselhd = item.source === 'faselhd';
        const isSahid4u = item.source === 'sahid4u';
        const isRoyal = item.source === 'royaldrama';
        const badgeText = isEgyDead ? (item.type || 'movie') : isWecima ? (item.type || 'movie') : isFaselhd ? (item.type || 'movie') : isSahid4u ? (item.type || 'movie') : isRoyal ? (item.type || 'movie') : type;
        const badgeClass = isEgyDead ? 'type-badge badge-egydead' : isWecima ? 'type-badge badge-wecima' : isFaselhd ? 'type-badge badge-faselhd' : isSahid4u ? 'type-badge badge-sahid4u' : isRoyal ? 'type-badge badge-royaldrama' : 'type-badge';
        let sourceTag;
        if (isEgyDead) {
            sourceTag = '<span class="source-badge source-egydead">EgyDead</span>';
        } else if (isWecima) {
            sourceTag = '<span class="source-badge source-wecima">Wecima</span>';
        } else if (isFaselhd) {
            sourceTag = '<span class="source-badge source-faselhd">FaselHD</span>';
        } else if (isSahid4u) {
            sourceTag = '<span class="source-badge source-sahid4u">Sahid4u</span>';
        } else if (isRoyal) {
            sourceTag = '<span class="source-badge source-royaldrama">Royal Drama</span>';
        } else {
            sourceTag = '<span class="source-badge source-akwam">Akwam</span>';
        }

        // Thumbnail for external source results
        const posterUrl = safeRemoteUrl(isEgyDead ? item.thumbnail : (item.poster || item.thumbnail || ''));
        const thumbUrl = posterUrl ? (isEgyDead || isWecima ? `https://corsproxy.io/?${encodeURIComponent(posterUrl)}` : posterUrl) : null;
        const itemName = escapeHtml(item.name || 'Untitled');
        const safeBadgeText = escapeHtml(badgeText);
        const thumbHtml = thumbUrl
            ? `<div class="result-thumb"><img src="${escapeHtml(thumbUrl)}" alt="Poster for ${itemName}" width="102" height="142" loading="lazy"></div>`
            : '';

        const shell = document.createElement('div');
        shell.className = 'result-card-shell';
        const div = document.createElement('button');
        div.type = 'button';
        div.className = 'result-item' + (thumbHtml ? ' has-thumb' : '');
        div.setAttribute('aria-label', `Open ${item.name || 'title'}`);
        div.innerHTML = `
            ${thumbHtml}
            <div class="result-info">
                <div class="result-header">
                    <div style="display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">
                        ${sourceTag}
                        <span class="${badgeClass}">${safeBadgeText}</span>
                    </div>
                </div>
                <h3 dir="auto">${itemName}</h3>
            </div>
        `;
        const fav = document.createElement('button');
        fav.className = `fav-toggle ${isFav ? 'active' : ''}`;
        fav.title = isFav ? 'Remove from favorites' : 'Add to favorites';
        fav.setAttribute('aria-label', fav.title);
        fav.setAttribute('aria-pressed', String(isFav));
        fav.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>`;
        const poster = div.querySelector('.result-thumb img');
        poster?.addEventListener('error', () => {
            poster.parentElement.remove();
            div.classList.remove('has-thumb');
        }, { once: true });
        fav.onclick = () => toggleFavorite(item, badgeText);
        div.onclick = () => { state.modalHistory = []; handleItemClick(item, badgeText); };
        shell.append(div, fav);
        dom.resultsGrid.appendChild(shell);
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
        const isWecima = item.source === 'wecima';
        const isFaselhd = item.source === 'faselhd';
        const isSahid4u = item.source === 'sahid4u';
        const isRoyal = item.source === 'royaldrama';
        let sourceTag;
        if (isEgyDead) {
            sourceTag = '<span class="source-badge source-egydead">EgyDead</span>';
        } else if (isWecima) {
            sourceTag = '<span class="source-badge source-wecima">Wecima</span>';
        } else if (isFaselhd) {
            sourceTag = '<span class="source-badge source-faselhd">FaselHD</span>';
        } else if (isSahid4u) {
            sourceTag = '<span class="source-badge source-sahid4u">Sahid4u</span>';
        } else if (isRoyal) {
            sourceTag = '<span class="source-badge source-royaldrama">Royal Drama</span>';
        } else {
            sourceTag = '<span class="source-badge source-akwam">Akwam</span>';
        }
        const shell = document.createElement('div');
        shell.className = 'drawer-item-shell';
        const div = document.createElement('button');
        div.type = 'button';
        div.className = 'drawer-item';
        div.setAttribute('aria-label', `Open ${item.name || 'title'}`);
        div.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div style="display:flex;gap:0.4rem;">${sourceTag}<span class="type-badge">${escapeHtml(item.type)}</span></div>
            </div>
            <h4 dir="auto">${escapeHtml(item.name || 'Untitled')}</h4>
        `;
        const fav = document.createElement('button');
        fav.className = 'fav-toggle active';
        fav.setAttribute('aria-label', 'Remove from favorites');
        fav.setAttribute('aria-pressed', 'true');
        fav.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>';
        fav.onclick = () => toggleFavorite(item, item.type);
        div.onclick = () => { closeDrawer(); state.modalHistory = []; handleItemClick(item, item.type); };
        shell.append(div, fav);
        dom.favoritesList.appendChild(shell);
    });
}

// ============================================================
//  Unified click dispatcher
// ============================================================
function handleItemClick(item, type) {
    state.activeItem = { ...item, type };
    if (item.source === 'egydead') {
        handleEgyDeadClick(item);
    } else if (item.source === 'wecima') {
        handleWecimaClick(item);
    } else if (item.source === 'faselhd') {
        handleFaselhdClick(item);
    } else if (item.source === 'sahid4u') {
        handleSahid4uClick(item);
    } else if (item.source === 'royaldrama') {
        handleRoyaldramaClick(item);
    } else {
        handleAkwamClick(item, type);
    }
}

// ============================================================
//  AKWAM flow  (unchanged logic, just renamed for clarity)
// ============================================================
async function handleAkwamClick(item, type, isBackAction = false) {
    if (type === 'series') {
        openModal('Select Episode', state.modalHistory.length > 0);
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

        const gridDiv = document.createElement('div');
        gridDiv.className = 'episodes-grid';

        state.currentEpisodes.forEach((ep, index) => {
            const row = document.createElement('div');
            row.className = 'list-item episode-item';
            row.innerText = `${index + 1}. ${ep.name}`;
            row.onclick = () => {
                state.activeItem = { name: ep.name, url: ep.url, source: 'akwam', type: 'movie' };
                dom.shareModalBtn.style.display = 'flex';
                state.modalHistory.push(currentViewRenderer);
                handleQualitySelect(ep.url);
            };
            gridDiv.appendChild(row);
        });
        dom.modalList.appendChild(gridDiv);
    } else {
        handleQualitySelect(item.url);
    }
}

async function handleQualitySelect(url) {
    openModal('Select Quality', state.modalHistory.length > 0);
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
    openModal('Finalizing Link', state.modalHistory.length > 0);
    dom.modalList.innerHTML = `
        <div style="text-align:center;padding:2.5rem;">
            <p style="margin-bottom:2rem;color:var(--text-secondary);">Preparing your secure direct link...</p>
            <div class="spinner" style="margin:0 auto;"></div>
        </div>`;
    const data = await apiResolve(link_id);
    if (data.url) renderFinalUrlScreen(data.url, link_id);
    else dom.modalList.innerHTML = '<p style="color:var(--danger);text-align:center;padding:2rem;">Error resolving link. Try another quality.</p>';
}

function renderFinalUrlScreen(url, linkId) {
    openModal('Direct Link', state.modalHistory.length > 0);
    const isDirectMp4 = url.includes('.mp4') || url.includes('.mkv');
    
    let actionBtns = '';
    if (isDirectMp4) {
        actionBtns = `
            <a href="${url}" class="btn-primary" style="text-align:center;text-decoration:none;" target="_blank">
                DOWNLOAD VIA BROWSER
            </a>
            <button class="btn-secondary" style="border-color:var(--warning);color:var(--warning);padding:0.85rem;" id="btnStream">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:0.3rem;"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                Stream Online
            </button>
        `;
    } else {
        actionBtns = `
            <a href="${url}" class="btn-primary" style="text-align:center;text-decoration:none;" target="_blank">
                OPEN DOWNLOAD PAGE
            </a>
            <p style="color:var(--text-secondary);font-size:0.85rem;text-align:center;margin-top:0.5rem;">
                This is a secure Akwam page. Open it in your browser to start the final download.
            </p>
        `;
    }

    dom.modalList.innerHTML = `
        <div class="result-container">
            <p class="result-label">${isDirectMp4 ? 'Direct Link:' : 'Download Page:'}</p>
            <div class="link-display-box">
                <code class="raw-url">${url}</code>
                <button class="btn-secondary btn-sm" id="btnCopySingle">COPY</button>
            </div>
            <div style="margin-top:1.5rem;display:flex;flex-direction:column;gap:0.75rem;">
                ${actionBtns}
            </div>
        </div>`;
    
    document.getElementById('btnCopySingle').onclick = e => copyLinkToClipboard(url, e.target);
    const streamBtn = document.getElementById('btnStream');
    if (streamBtn) streamBtn.onclick = () => playVideo(url, linkId);
}

function playVideo(url, linkId) {
    state.modalHistory.push(() => renderFinalUrlScreen(url, linkId));
    openModal('Playing Video', state.modalHistory.length > 0, true);

    const isAkwamCdn = url.includes('downet.net') || url.includes('akwam');

    if (isAkwamCdn && linkId) {
        // Resolve a fresh signed URL for display/download. Embedded playback
        // uses the same-origin Akwam stream endpoint because a subset of
        // Downet shards currently have a broken public TLS certificate chain.
        dom.modalList.innerHTML = `
            <div style="text-align:center;padding:3rem;">
                <div class="spinner" style="margin:0 auto 1.5rem;width:36px;height:36px;"></div>
                <p style="color:var(--text-secondary);margin-bottom:0.5rem;">Bypassing CDN protection...</p>
                <p style="color:var(--text-muted);font-size:0.8rem;">Resolving the direct download link. Takes ~3 seconds.</p>
            </div>`;

        AkwamWorker.resolveStream(linkId)
            .then(data => data)
            .then(data => {
                if (data.url) {
                    const mp4Url = data.url;
                    dom.modalList.innerHTML = `
                        <div style="padding:1.5rem;text-align:center;">
                            <div style="margin-bottom:1.5rem;">
                                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:0.75rem;">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                </svg>
                                <p style="color:var(--text-primary);font-weight:600;font-size:1.05rem;margin-bottom:0.25rem;">Stream Ready</p>
                                <p style="color:var(--text-secondary);font-size:0.8rem;">Use protected playback here or open the direct fallback.</p>
                            </div>
                            <div class="link-display-box" style="margin-bottom:1.5rem;">
                                <code class="raw-url" style="font-size:0.7rem;word-break:break-all;">${mp4Url}</code>
                                <button class="btn-secondary btn-sm" id="btnCopyStream">COPY</button>
                            </div>
                            <div style="display:flex;flex-direction:column;gap:0.75rem;">
                                <a href="${mp4Url}" class="btn-primary" style="text-align:center;text-decoration:none;" target="_blank" rel="noopener noreferrer" id="btnOpenStream">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:0.3rem;">
                                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                                    </svg>
                                    OPEN VIDEO IN NEW TAB
                                </a>
                                <button class="btn-secondary" id="btnTryEmbed" style="padding:0.85rem;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:0.3rem;">
                                        <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
                                        <line x1="7" y1="2" x2="7" y2="22"></line>
                                        <line x1="17" y1="2" x2="17" y2="22"></line>
                                        <line x1="2" y1="12" x2="22" y2="12"></line>
                                        <line x1="2" y1="7" x2="7" y2="7"></line>
                                        <line x1="2" y1="17" x2="7" y2="17"></line>
                                        <line x1="17" y1="17" x2="22" y2="17"></line>
                                        <line x1="17" y1="7" x2="22" y2="7"></line>
                                    </svg>
                                    PLAY HERE
                                </button>
                            </div>
                            <p style="color:var(--text-muted);font-size:0.7rem;margin-top:1rem;">
                                Protected playback preserves seeking and avoids host TLS/CORS failures. If it is unavailable, use "Open Video in New Tab".
                            </p>
                        </div>`;
                    
                    document.getElementById('btnCopyStream').onclick = e => copyLinkToClipboard(mp4Url, e.target);
                    document.getElementById('btnTryEmbed').onclick = () => {
                        const proxyUrl = `/api/akwam-stream?url=${encodeURIComponent(linkId)}`;
                        dom.modalList.innerHTML = `
                            <div style="padding:1rem;width:100%;display:flex;flex-direction:column;background:var(--video-bg);border-radius:var(--radius);overflow:hidden;">
                                <video id="akwamVideo" src="${proxyUrl}" controls autoplay playsinline style="width:100%;max-height:70vh;outline:none;background:var(--video-bg);border-radius:var(--radius);object-fit:contain;">
                                    Your browser does not support HTML5 video.
                                </video>
                                <p id="streamStatus" style="color:var(--text-secondary);font-size:0.8rem;text-align:center;padding:0.5rem;">Loading protected stream...</p>
                            </div>`;
                        const video = document.getElementById('akwamVideo');
                        const status = document.getElementById('streamStatus');
                        if (video) {
                            const showPlaybackFallback = message => {
                                if (status) {
                                    status.style.color = '#f87171';
                                    status.innerHTML = message + ' <a href="' + mp4Url + '" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:underline;">Open in new tab instead</a>';
                                }
                            };
                            video._playbackTimer = setTimeout(() => {
                                showPlaybackFallback('Protected playback timed out.');
                            }, 20000);
                            video.addEventListener('canplay', () => {
                                clearTimeout(video._playbackTimer);
                                if (status) status.textContent = '';
                            }, { once: true });
                            video.addEventListener('error', () => {
                                if (video._tearingDown) return;
                                clearTimeout(video._playbackTimer);
                                showPlaybackFallback('Embedded playback failed.');
                            }, { once: true });
                        }
                    };
                } else {
                    dom.modalList.innerHTML = '<p style="color:var(--danger);text-align:center;padding:2rem;">Failed to resolve stream URL. Try again.</p>';
                }
            })
            .catch(err => {
                dom.modalList.innerHTML = `<p style="color:var(--danger);text-align:center;padding:2rem;">Error: ${err.message}</p>`;
            });
        return;
    }

    // Non-Akwam videos: play directly in embedded player
    dom.modalList.innerHTML = `
        <div style="padding:1rem;width:100%;display:flex;flex-direction:column;background:var(--video-bg);border-radius:var(--radius);overflow:hidden;">
            <video id="akwamVideo" controls autoplay playsinline style="width:100%;max-height:70vh;outline:none;background:var(--video-bg);border-radius:var(--radius);object-fit:contain;">
                <source src="${url}" type="video/mp4">
                Your browser does not support HTML5 video.
            </video>
        </div>`;
}



async function handleBulkResolve(episodesToResolve) {
    if (!episodesToResolve || episodesToResolve.length === 0) return;
    openModal('Bulk Resolving...', state.modalHistory.length > 0);
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
            state.activeItem = { name: ep.name, url: ep.url, source: 'egydead', type: 'episode' };
            dom.shareModalBtn.style.display = 'flex';
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
    const servers    = playableServers(data.servers);
    const directUrls = data.direct_urls || [];
    const downloads  = data.downloads  || [];

    // ── Case 1: we have servers ──────────────────────
    if (servers.length > 0) {
        dom.mainModal.classList.add('modal-wide');
        dom.modalTitle.innerText = item.name;

        let serverBtns = '';
        if (servers.length > 1) {
            serverBtns = servers.map((s, i) =>
                `<button class="server-btn ${i === 0 ? 'active' : ''}" data-src="${escapeHtml(s.url)}" onclick="egyDeadSwitchServer(this)">${escapeHtml(s.name)}</button>`
            ).join('');
        }

        // Build download buttons HTML — grouped by QUALITY, not by server
        const downloadIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;
        let downloadsHtml = '';
        if (downloads.length > 0) {
            // 1. Group by quality
            const qualityMap = {};
            for (const d of downloads) {
                if (!qualityMap[d.quality]) qualityMap[d.quality] = [];
                qualityMap[d.quality].push(d);
            }

            // 2. Sort qualities: 4K → 2160p → 1080p → 720p → 480p → rest
            const qualityOrder = ['4K', '2160p', '1080p', '720p', '480p', '360p', '240p'];
            const sortedQualities = Object.keys(qualityMap).sort((a, b) => {
                const ai = qualityOrder.indexOf(a);
                const bi = qualityOrder.indexOf(b);
                return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
            });

            // 3. One card per quality — servers for that quality listed as chips inside
            const qualityCards = sortedQualities.map(q => {
                const serversForQuality = qualityMap[q];
                const serverChips = serversForQuality.map(d => {
                    const label = d.name && d.name !== 'Direct Download' ? d.name : 'Mirror';
                    return `<a class="dl-server-chip" href="${d.url}" target="_blank" rel="noopener noreferrer">${downloadIcon} ${label}</a>`;
                }).join('');
                return `<div class="dl-quality-card">
                    <span class="dl-quality-label">${q}</span>
                    <div class="dl-server-chips">${serverChips}</div>
                </div>`;
            }).join('');

            downloadsHtml = `
                <div class="downloads-section">
                    <div class="downloads-label">Downloads</div>
                    <div class="dl-quality-list">${qualityCards}</div>
                </div>`;
        }

        dom.modalList.innerHTML = `
            <div class="watch-container">
                ${serverBtns ? `<div class="server-row">${serverBtns}</div>` : ''}
                ${renderPlayerFrame('egyDeadFrame', servers[0].url, `EgyDead — ${servers[0].name}`)}
                ${downloadsHtml}
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

    // Even without servers/direct_urls, downloads may have been found
    let downloadsHtml = '';
    if (downloads.length > 0) {
        const downloadIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;
        const qualityMap = {};
        for (const d of downloads) {
            if (!qualityMap[d.quality]) qualityMap[d.quality] = [];
            qualityMap[d.quality].push(d);
        }
        const qualityOrder = ['4K', '2160p', '1080p', '720p', '480p', '360p', '240p'];
        const sortedQualities = Object.keys(qualityMap).sort((a, b) => {
            const ai = qualityOrder.indexOf(a);
            const bi = qualityOrder.indexOf(b);
            return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
        });
        const qualityCards = sortedQualities.map(q => {
            const serversForQuality = qualityMap[q];
            const serverChips = serversForQuality.map(d => {
                const label = d.name && d.name !== 'Direct Download' ? d.name : 'Mirror';
                return `<a class="dl-server-chip" href="${d.url}" target="_blank" rel="noopener noreferrer">${downloadIcon} ${label}</a>`;
            }).join('');
            return `<div class="dl-quality-card">
                <span class="dl-quality-label">${q}</span>
                <div class="dl-server-chips">${serverChips}</div>
            </div>`;
        }).join('');
        downloadsHtml = `
            <div class="downloads-section" style="border-top:none;padding-top:0;">
                <div class="downloads-label">Downloads Available</div>
                <div class="dl-quality-list">${qualityCards}</div>
            </div>`;
    }

    dom.modalList.innerHTML = `
        <div style="text-align:center;padding:2rem;">
            <p style="color:var(--text-secondary);margin-bottom:1.5rem;">
                Could not extract a direct stream.${downloads.length > 0 ? ' But download links are available below.' : ' Open the page in your browser to watch.'}
            </p>
            ${downloadsHtml}
            <a href="${item.url}" target="_blank" class="btn-primary" style="display:inline-block;text-decoration:none;margin-top:1rem;">
                OPEN IN EGYDEAD
            </a>
        </div>`;
}

// Switch embed server
window.egyDeadSwitchServer = btn => {
    switchPlayerServer(btn, 'egyDeadFrame');
};

// ============================================================
//  FASELHD flow
// ============================================================
async function handleFaselhdClick(item) {
    state.modalHistory = [];
    if (item.type === 'series') {
        await faselhdShowSeries(item);
    } else {
        await faselhdShowDetail(item);
    }
}

async function faselhdShowSeries(item) {
    openModal(item.name, false);
    showModalLoading(true);
    const slug = item.slug || item.url.split('/').pop();
    const data = await faselhdSeries(slug);
    showModalLoading(false);

    const seasons = data.seasons || [];
    if (seasons.length === 0 || data.type === 'movie') {
        await faselhdShowDetail(item);
        return;
    }

    dom.modalTitle.innerText = `${item.name} — Seasons`;
    const currentView = () => faselhdShowSeries(item);

    seasons.forEach(s => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${s.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.modalHistory.push(currentView);
            faselhdShowEpisodes(item, s);
        };
        dom.modalList.appendChild(row);
    });
}

async function faselhdShowEpisodes(seriesItem, season) {
    openModal(`Season ${season.number || season.name}`, state.modalHistory.length > 0);
    showModalLoading(true);

    const slug = seriesItem.slug || seriesItem.url.split('/').pop();
    const data = await faselhdSeries(slug);
    showModalLoading(false);

    const seasons = data.seasons || [];
    const targetSeason = seasons.find(s => s.number === season.number || s.name === season.name);
    const episodes = (targetSeason && targetSeason.episodes) || [];

    dom.modalTitle.innerText = `${seriesItem.name} — ${season.name}`;

    if (episodes.length === 0) {
        dom.modalList.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:2rem;">No episodes found.</p>';
        return;
    }

    const currentView = () => faselhdShowEpisodes(seriesItem, season);

    episodes.forEach((ep, idx) => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${idx + 1}. ${ep.title || ep.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.activeItem = { name: ep.title || ep.name, url: ep.url || '', source: 'faselhd', type: 'movie', post_id: ep.post_id || ep.id };
            dom.shareModalBtn.style.display = 'flex';
            state.modalHistory.push(currentView);
            faselhdShowDetail(state.activeItem);
        };
        dom.modalList.appendChild(row);
    });
}

async function faselhdShowDetail(item) {
    openModal('Loading…', state.modalHistory.length > 0);
    showModalLoading(true);

    let detail;
    const postId = item.post_id || item.id;
    if (postId) {
        detail = await faselhdPostDetail(postId);
    } else {
        // Try to get post_id from search
        const searchRes = await faselhdSearch(item.name);
        const found = (searchRes.results || []).find(r => r.url === item.url || r.name === item.name);
        const foundId = found && (found.post_id || found.id);
        if (foundId) {
            detail = await faselhdPostDetail(foundId);
        }
    }
    showModalLoading(false);

    const servers = playableServers(detail && detail.servers);
    const downloads = (detail && detail.downloads) || [];
    const name = (detail && detail.title) || item.name;

    dom.mainModal.classList.add('modal-wide');
    dom.modalTitle.innerText = name;

    if (servers.length > 0) {
        let serverBtns = '';
        if (servers.length > 1) {
            serverBtns = servers.map((s, i) =>
                        `<button class="server-btn ${i === 0 ? 'active' : ''}" data-src="${escapeHtml(s.url)}" onclick="faselhdSwitchServer(this)">${escapeHtml(s.name || `Server ${i + 1}`)}</button>`
                    ).join('');
        }

        // Build downloads HTML
        let downloadsHtml = '';
        if (downloads.length > 0) {
            const dlCards = downloads.map(d =>
                `<a class="dl-server-chip" href="${d.url}" target="_blank" rel="noopener noreferrer">${d.quality || d.name} (${d.size || ''})</a>`
            ).join('');
            downloadsHtml = `
                <div class="downloads-section">
                    <div class="downloads-label">Downloads</div>
                    <div class="dl-quality-list">
                        <div class="dl-quality-card">
                            <div class="dl-server-chips">${dlCards}</div>
                        </div>
                    </div>
                </div>`;
        }

        dom.modalList.innerHTML = `
            <div class="watch-container">
                ${serverBtns ? `<div class="server-row">${serverBtns}</div>` : ''}
                ${renderPlayerFrame('faselhdFrame', servers[0].url, `FaselHD — ${servers[0].name}`)}
                ${downloadsHtml}
            </div>`;
    } else if (downloads.length > 0) {
        const dlCards = downloads.map(d =>
            `<a class="dl-server-chip" href="${d.url}" target="_blank" rel="noopener noreferrer">${d.quality || d.name} (${d.size || ''})</a>`
        ).join('');
        dom.modalList.innerHTML = `
            <div class="watch-container">
                <p style="color:var(--text-secondary);text-align:center;padding:1rem;">No streaming servers available. Download links below.</p>
                <div class="downloads-section">
                    <div class="downloads-label">Downloads</div>
                    <div class="dl-quality-list">
                        <div class="dl-quality-card">
                            <div class="dl-server-chips">${dlCards}</div>
                        </div>
                    </div>
                </div>
            </div>`;
    } else {
        dom.modalList.innerHTML = `
            <div style="text-align:center;padding:2rem;">
                <p style="color:var(--text-secondary);margin-bottom:1.5rem;">Could not extract servers or downloads.</p>
            </div>`;
    }
}

window.faselhdSwitchServer = btn => {
    switchPlayerServer(btn, 'faselhdFrame');
};

// ============================================================
//  WECIMA flow
// ============================================================
async function handleWecimaClick(item) {
    state.modalHistory = [];
    if (item.type === 'series') {
        await wecimaShowSeries(item);
    } else {
        await wecimaShowDetail(item);
    }
}

async function wecimaShowSeries(item) {
    openModal(item.name, false);
    showModalLoading(true);
    const data = await wecimaSeries(item.url);
    showModalLoading(false);

    const seasons = data.seasons || [];
    const episodes = data.episodes || [];
    const postId = data.post_id;

    // If single season with episodes already on page, show them directly
    if (seasons.length <= 1 && episodes.length > 0) {
        await wecimaShowEpisodes(item, { season_number: 1, name: 'Season 1' }, episodes);
        return;
    }

    if (seasons.length === 0) {
        await wecimaShowDetail(item);
        return;
    }

    dom.modalTitle.innerText = `${item.name} — Seasons`;
    const currentView = () => wecimaShowSeries(item);

    seasons.forEach(s => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${s.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.modalHistory.push(currentView);
            wecimaShowEpisodes(item, s, null, postId);
        };
        dom.modalList.appendChild(row);
    });
}

async function wecimaShowEpisodes(seriesItem, season, preloadedEpisodes, postId) {
    openModal(`Season ${season.season_number}`, state.modalHistory.length > 0);
    showModalLoading(true);

    let episodes = preloadedEpisodes || [];

    // Load episodes via AJAX if not preloaded
    if (episodes.length === 0 && postId) {
        const data = await wecimaEpisodes(postId, season.season_number);
        episodes = data.episodes || [];
    }

    showModalLoading(false);
    dom.modalTitle.innerText = `${seriesItem.name} — S${season.season_number}`;

    if (episodes.length === 0) {
        dom.modalList.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:2rem;">No episodes found.</p>';
        return;
    }

    const currentView = () => wecimaShowEpisodes(seriesItem, season, episodes, postId);

    episodes.forEach((ep, idx) => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${idx + 1}. ${ep.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.activeItem = { name: ep.name, url: ep.url, source: 'wecima', type: 'episode' };
            dom.shareModalBtn.style.display = 'flex';
            state.modalHistory.push(currentView);
            wecimaShowDetail(ep);
        };
        dom.modalList.appendChild(row);
    });
}

async function wecimaShowDetail(item) {
    openModal(`Loading…`, state.modalHistory.length > 0);
    showModalLoading(true);
    const data = await wecimaDetail(item.url);
    showModalLoading(false);

    const metadata = data.metadata || {};
    const servers = playableServers(data.servers);
    const downloads = data.downloads || [];
    const name = metadata.name || item.name;

    dom.mainModal.classList.add('modal-wide');
    dom.modalTitle.innerText = name;

    // Build server buttons with "open in new tab" fallback per server
    let serverBtns = '';
    if (servers.length > 0) {
        serverBtns = servers.map((s, i) => `
            <div class="server-btn-wrap ${i === 0 ? 'active' : ''}">
                <button class="server-btn" data-src="${escapeHtml(s.url)}" onclick="wecimaSwitchServer(this)">
                    ${escapeHtml(s.name)}
                </button>
                <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="server-ext-link" title="Open in new tab">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                </a>
            </div>
        `).join('');
    }

    // Build download links
    const downloadIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`;
    let downloadsHtml = '';
    if (downloads.length > 0) {
        const dlCards = downloads.map(d =>
            `<a class="dl-server-chip" href="${d.url}" target="_blank" rel="noopener noreferrer">${downloadIcon} ${d.name}</a>`
        ).join('');
        downloadsHtml = `
            <div class="downloads-section">
                <div class="downloads-label">Downloads</div>
                <div class="dl-quality-list">
                    <div class="dl-quality-card">
                        <div class="dl-server-chips">${dlCards}</div>
                    </div>
                </div>
            </div>`;
    }

    if (servers.length > 0) {
        dom.modalList.innerHTML = `
            <div class="watch-container">
                <div class="server-row" style="flex-wrap:wrap;gap:0.35rem;">${serverBtns}</div>
                ${renderPlayerFrame('wecimaFrame', servers[0].url, `Wecima — ${servers[0].name}`, `
                    <div id="wecimaFrameFallback" style="display:none;text-align:center;padding:3rem;">
                        <p style="color:var(--text-secondary);margin-bottom:1rem;">The embed player didn't load. Try opening it directly.</p>
                        <a href="${escapeHtml(servers[0].url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="text-decoration:none;display:inline-block;">
                            OPEN IN NEW TAB
                        </a>
                    </div>`)}
                ${downloadsHtml}
            </div>`;

        // Handle iframe load error
        const frame = document.getElementById('wecimaFrame');
        frame.onerror = () => {
            frame.style.display = 'none';
            document.getElementById('wecimaFrameFallback').style.display = 'block';
        };
        // Some embed hosts don't trigger onerror for cross-origin, so add a timeout fallback
        setTimeout(() => {
            try {
                if (frame.contentDocument && frame.contentDocument.body.innerHTML.trim() === '') {
                    frame.style.display = 'none';
                    document.getElementById('wecimaFrameFallback').style.display = 'block';
                }
            } catch(e) {
                // cross-origin - can't check, assume it's loading
            }
        }, 8000);
    } else if (downloads.length > 0) {
        dom.modalList.innerHTML = `
            <div class="watch-container">
                <p style="color:var(--text-secondary);text-align:center;padding:1rem;">No streaming servers available. Download links below.</p>
                ${downloadsHtml}
            </div>`;
    } else {
        dom.modalList.innerHTML = `
            <div style="text-align:center;padding:2rem;">
                <p style="color:var(--text-secondary);margin-bottom:1.5rem;">Could not extract servers or downloads.</p>
                <a href="${item.url}" target="_blank" class="btn-primary" style="display:inline-block;text-decoration:none;">
                    OPEN IN WECIMA
                </a>
            </div>`;
    }
}

window.wecimaSwitchServer = btn => {
    switchPlayerServer(btn, 'wecimaFrame');
    const frame = document.getElementById('wecimaFrame');
    const fallback = document.getElementById('wecimaFrameFallback');
    if (frame) {
        frame.style.display = 'block';
        if (fallback) fallback.style.display = 'none';
        // Update fallback link
        const fallbackLink = fallback?.querySelector('a');
        if (fallbackLink) fallbackLink.href = btn.dataset.src;
    }
};

// ============================================================
//  SAHID4U flow
// ============================================================
async function handleSahid4uClick(item) {
    state.modalHistory = [];
    if (item.type === 'series') {
        await sahid4uShowSeasons(item);
    } else {
        await sahid4uShowWatch(item);
    }
}

async function sahid4uShowSeasons(item) {
    openModal(item.name, false);
    showModalLoading(true);
    const data = await sahid4uGetSeasons(item.url);
    showModalLoading(false);

    const seasons = data.seasons || [];
    if (seasons.length === 0) {
        await sahid4uShowWatch(item);
        return;
    }

    dom.modalTitle.innerText = `${item.name} — Seasons`;
    const currentView = () => sahid4uShowSeasons(item);

    seasons.forEach(s => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${s.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.modalHistory.push(currentView);
            sahid4uShowEpisodes(s);
        };
        dom.modalList.appendChild(row);
    });
}

async function sahid4uShowEpisodes(seasonItem) {
    openModal(`${seasonItem.name}`, state.modalHistory.length > 0);
    showModalLoading(true);
    const data = await sahid4uGetEpisodes(seasonItem.url);
    showModalLoading(false);

    const episodes = data.episodes || [];
    dom.modalTitle.innerText = `${seasonItem.name} — Episodes`;

    if (episodes.length === 0) {
        dom.modalList.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:2rem;">No episodes found.</p>';
        return;
    }

    const currentView = () => sahid4uShowEpisodes(seasonItem);

    episodes.forEach((ep, idx) => {
        const row = document.createElement('div');
        row.className = 'list-item';
        row.innerHTML = `<span>${idx + 1}. ${ep.name}</span><span class="size-tag">▶</span>`;
        row.onclick = () => {
            state.activeItem = { name: ep.name, url: ep.url, source: 'sahid4u', type: 'episode' };
            dom.shareModalBtn.style.display = 'flex';
            state.modalHistory.push(currentView);
            sahid4uShowWatch(ep);
        };
        dom.modalList.appendChild(row);
    });
}

async function sahid4uShowWatch(item) {
    openModal('Loading…', state.modalHistory.length > 0);
    showModalLoading(true);

    const data = await sahid4uGetWatchDownload(item.url);
    showModalLoading(false);

    const servers = playableServers(data.servers);
    const qualities = data.qualities || [];

    dom.mainModal.classList.add('modal-wide');
    dom.modalTitle.innerText = item.name;

    // Build server buttons
    let serverBtns = '';
    if (servers.length > 1) {
        serverBtns = servers.map((s, i) =>
            `<button class="server-btn ${i === 0 ? 'active' : ''}" data-src="${escapeHtml(s.url)}" onclick="sahid4uSwitchServer(this)">${escapeHtml(s.name)}</button>`
        ).join('');
    }

    // Build quality badges HTML
    let qualitiesHtml = '';
    if (qualities.length > 0) {
        const badges = qualities.map(q =>
            `<span class="dl-server-chip">${q}</span>`
        ).join('');
        qualitiesHtml = `
            <div class="downloads-section">
                <div class="downloads-label">Available Qualities</div>
                <div class="dl-quality-list">
                    <div class="dl-quality-card">
                        <div class="dl-server-chips">${badges}</div>
                    </div>
                </div>
            </div>`;
    }

    if (servers.length > 0) {
        dom.modalList.innerHTML = `
            <div class="watch-container">
                ${serverBtns ? `<div class="server-row">${serverBtns}</div>` : ''}
                ${renderPlayerFrame('sahid4uFrame', servers[0].url, `Sahid4u — ${servers[0].name}`)}
                ${qualitiesHtml}
                <a href="${item.url}" target="_blank" class="btn-secondary btn-open-page">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    Open in Sahid4u
                </a>
            </div>`;
    } else if (qualities.length > 0) {
        dom.modalList.innerHTML = `
            <div class="watch-container">
                <p style="color:var(--text-secondary);text-align:center;padding:1rem;">No streaming servers available.</p>
                ${qualitiesHtml}
            </div>`;
    } else {
        dom.modalList.innerHTML = `
            <div style="text-align:center;padding:2rem;">
                <p style="color:var(--text-secondary);margin-bottom:1.5rem;">Could not extract servers or quality info.</p>
                <a href="${item.url}" target="_blank" class="btn-primary" style="display:inline-block;text-decoration:none;">
                    OPEN IN SAHID4U
                </a>
            </div>`;
    }
}

window.sahid4uSwitchServer = btn => {
    switchPlayerServer(btn, 'sahid4uFrame');
};

// ============================================================
//  ROYAL-DRAMA flow
// ============================================================
async function royaldramaSearch(q) {
    const res = await fetch(`/api/royaldrama/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    return data.results || [];
}
async function royaldramaHome() {
    const res = await fetch('/api/royaldrama/home');
    const data = await res.json();
    return (data.items || []).map(r => ({ ...r, source: 'royaldrama' }));
}
async function royaldramaBrowseSeries(page = 1) {
    const res = await fetch(`/api/royaldrama/series?page=${page}`);
    const data = await res.json();
    return (data.items || []).map(r => ({ ...r, source: 'royaldrama' }));
}
async function royaldramaBrowseMovies(page = 1) {
    const res = await fetch(`/api/royaldrama/movies?page=${page}`);
    const data = await res.json();
    return (data.items || []).map(r => ({ ...r, source: 'royaldrama' }));
}
async function royaldramaBrowseEpisodes(page = 1) {
    const res = await fetch(`/api/royaldrama/episodes?page=${page}`);
    const data = await res.json();
    return (data.items || []).map(r => ({ ...r, source: 'royaldrama' }));
}
async function royaldramaBrowseCategory(slug, page = 1) {
    const res = await fetch(`/api/royaldrama/category?slug=${slug}`);
    const data = await res.json();
    return (data.items || []).map(r => ({ ...r, source: 'royaldrama' }));
}
async function royaldramaDetail(url) {
    const res = await fetch(`/api/royaldrama/detail?url=${encodeURIComponent(url)}`);
    return res.json();
}

async function handleRoyaldramaClick(item) {
    state.modalHistory = [];
    await royaldramaShowDetail(item);
}

async function royaldramaShowDetail(item) {
    openModal(item.name || 'Royal Drama', state.modalHistory.length > 0);
    showModalLoading(true);
    const data = await royaldramaDetail(item.url);
    showModalLoading(false);

    const meta = data.metadata || {};
    const name = meta.name || item.name;
    const poster = meta.poster || '';
    const episodes = data.episodes || [];
    const isEpisode = item.type === 'episode';
    const isSeries = data.type === 'series' && episodes.length > 0;

    dom.mainModal.classList.add('modal-wide');
    dom.modalTitle.innerText = name;

    // Episode watch pages also contain the parent series episode list. Respect
    // the searched item and play it directly instead of reopening 100+ rows.
    if (isEpisode) {
        royaldramaPlay(item.url, name, poster, data.servers || []);
        return;
    }

    if (isSeries) {
        royaldramaEpisodes = episodes;
        royaldramaSeriesName = name;
        royaldramaPoster = poster;
        const currentView = () => royaldramaShowDetail(item);
        dom.modalList.innerHTML = `
            <div style="text-align:center;padding:0 0 1rem;">
                ${poster ? `<img src="${poster}" alt="" style="max-height:160px;border-radius:8px;margin-bottom:.75rem;">` : ''}
                <p style="color:var(--text-secondary);">${episodes.length} episodes — pick one to play.</p>
            </div>`;
        episodes.forEach((ep, idx) => {
            const row = document.createElement('div');
            row.className = 'list-item';
            row.innerHTML = `<span>${idx + 1}. ${ep.name}</span><span class="size-tag">▶</span>`;
            row.onclick = () => {
                state.activeItem = { name: ep.name, url: ep.url, source: 'royaldrama', type: 'movie' };
                dom.shareModalBtn.style.display = 'flex';
                state.modalHistory.push(currentView);
                royaldramaPlayEpisode(idx);
            };
            dom.modalList.appendChild(row);
        });
        return;
    }

    // Movie (or series page without parsed episodes) → play the watch page.
    royaldramaPlay(item.url, name, poster, data.servers || []);
}

let royaldramaEpisodes = [];
let royaldramaSeriesName = '';
let royaldramaPoster = '';

async function royaldramaPlayEpisode(idx) {
    const eps = royaldramaEpisodes;
    const ep = eps[idx];
    if (!ep) return;
    openModal(`${royaldramaSeriesName} — ${ep.name}`, state.modalHistory.length > 0);
    
    // Fetch details for the episode to get its servers
    showModalLoading(true);
    const data = await royaldramaDetail(ep.url);
    showModalLoading(false);
    
    dom.mainModal.classList.add('modal-wide');
    const nextDisabled = idx <= 0 ? 'disabled' : '';
    const prevDisabled = idx >= eps.length - 1 ? 'disabled' : '';
    
    const servers = playableServers(data.servers);
    let serverBtns = '';
    let playerHtml = '';
    
    if (servers.length > 0) {
        if (servers.length > 1) {
            serverBtns = servers.map((s, i) =>
                `<button class="server-btn ${i === 0 ? 'active' : ''}" data-src="${escapeHtml(s.url)}" onclick="royaldramaSwitchServer(this)">${escapeHtml(s.name)}</button>`
            ).join('');
        }
        playerHtml = `
            ${serverBtns ? `<div class="server-row">${serverBtns}</div>` : ''}
            ${renderPlayerFrame('royaldramaFrame', servers[0].url, `Royal Drama — ${servers[0].name}`)}
        `;
    } else {
        playerHtml = `
            <div class="downloads-section">
                <p style="color:var(--text-secondary);font-size:.85rem;text-align:center;">
                    No direct player available for this episode.
                </p>
            </div>
        `;
    }
    
    dom.modalList.innerHTML = `
        <div class="watch-container">
            <div class="episode-nav">
                <button class="server-btn" ${prevDisabled} onclick="royaldramaPlayEpisode(${idx + 1})">◀ Prev</button>
                <span class="ep-nav-title" style="flex:1;text-align:center;font-weight:bold;">${ep.name}</span>
                <button class="server-btn" ${nextDisabled} onclick="royaldramaPlayEpisode(${idx - 1})">Next ▶</button>
            </div>
            ${playerHtml}
        </div>`;
}

async function royaldramaPlay(url, name, poster, servers = []) {
    openModal(name || 'Royal Drama', state.modalHistory.length > 0);
    dom.mainModal.classList.add('modal-wide');
    servers = playableServers(servers);
    
    let serverBtns = '';
    let playerHtml = '';
    
    if (servers.length > 0) {
        if (servers.length > 1) {
            serverBtns = servers.map((s, i) =>
                `<button class="server-btn ${i === 0 ? 'active' : ''}" data-src="${escapeHtml(s.url)}" onclick="royaldramaSwitchServer(this)">${escapeHtml(s.name)}</button>`
            ).join('');
        }
        playerHtml = `
            ${serverBtns ? `<div class="server-row">${serverBtns}</div>` : ''}
            ${renderPlayerFrame('royaldramaFrame', servers[0].url, `Royal Drama — ${servers[0].name}`)}
        `;
    } else {
        playerHtml = `
            <div class="downloads-section">
                <p style="color:var(--text-secondary);font-size:.85rem;text-align:center;">
                    No direct player available for this title.
                </p>
            </div>
        `;
    }
    
    dom.modalList.innerHTML = `
        <div class="watch-container">
            ${playerHtml}
        </div>`;
}

window.royaldramaSwitchServer = btn => {
    switchPlayerServer(btn, 'royaldramaFrame');
};

// ============================================================
//  Search dispatcher
// ============================================================
async function doSearch() {
    const q = dom.searchInput.value.trim();
    if (!q) {
        showToast('Enter a title to start searching.', 'warning');
        dom.searchInput.focus();
        return;
    }

    showLoading(true);
    dom.resultsGrid.innerHTML = '';
    state.results = [];

    try {
        if (state.provider === 'egydead') {
            const data = await egyDeadSearch(q);
            state.results = data.results || [];
            renderResults(state.results, 'egydead');
        } else if (state.provider === 'wecima') {
            const data = await wecimaSearch(q);
            state.results = data.results || [];
            renderResults(state.results, 'wecima');
        } else if (state.provider === 'faselhd') {
            const data = await faselhdSearch(q);
            state.results = (data.results || []).map(r => ({ ...r, source: 'faselhd', post_id: r.id }));
            renderResults(state.results, 'faselhd');
        } else if (state.provider === 'sahid4u') {
            const data = await sahid4uSearch(q);
            state.results = (data.results || []).map(r => ({ ...r, source: 'sahid4u' }));
            renderResults(state.results, 'sahid4u');
        } else if (state.provider === 'royaldrama') {
            const data = await royaldramaSearch(q);
            state.results = (data || []).map(r => ({ ...r, source: 'royaldrama' }));
            renderResults(state.results, 'royaldrama');
        } else {
            const data = await apiSearch(q, state.type);
            state.results = data.results || [];
            renderResults(state.results, state.type);
        }
    } catch (e) {
        renderEmptyState('error');
    } finally {
        showLoading(false);
    }
}

dom.searchBtn.onclick = doSearch;
dom.searchInput.onkeydown = e => { if (e.key === 'Enter') doSearch(); };


// ============================================================
//  Sharing & URL State Handling
// ============================================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerText = message;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function encodeShareData(obj) {
    try {
        const json = JSON.stringify(obj);
        return btoa(unescape(encodeURIComponent(json)))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');
    } catch (e) {
        console.error('Encoding error', e);
        return '';
    }
}

function decodeShareData(str) {
    try {
        let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
        while (base64.length % 4) {
            base64 += '=';
        }
        const json = decodeURIComponent(escape(atob(base64)));
        return JSON.parse(json);
    } catch (e) {
        console.error('Decoding error', e);
        return null;
    }
}

function shareActiveItem() {
    if (!state.activeItem) return;
    const data = {
        s: state.activeItem.source,
        t: state.activeItem.type,
        n: state.activeItem.name,
        u: state.activeItem.url
    };
    const code = encodeShareData(data);
    const shareUrl = `${window.location.origin}${window.location.pathname}?item=${code}`;

    if (navigator.share) {
        navigator.share({
            title: state.activeItem.name,
            text: `Watch ${state.activeItem.name} on ${dom.brandName.innerText || 'Vortex'}`,
            url: shareUrl
        }).catch(err => {
            copyShareUrl(shareUrl);
        });
    } else {
        copyShareUrl(shareUrl);
    }
}

function shareFavoritesList() {
    if (state.favorites.length === 0) {
        showToast('Your favorites list is empty.', 'warning');
        return;
    }
    const data = state.favorites.map(f => ({
        s: f.source,
        t: f.type,
        n: f.name,
        u: f.url,
        th: f.thumbnail
    }));
    const code = encodeShareData(data);
    const shareUrl = `${window.location.origin}${window.location.pathname}?favs=${code}`;

    if (navigator.share) {
        navigator.share({
            title: 'My Favorites List',
            text: `Check out my favorites list on ${dom.brandName.innerText || 'Vortex'}`,
            url: shareUrl
        }).catch(err => {
            copyShareUrl(shareUrl);
        });
    } else {
        copyShareUrl(shareUrl);
    }
}

function copyShareUrl(url) {
    navigator.clipboard.writeText(url)
        .then(() => showToast('Share link copied to clipboard!'))
        .catch(() => showToast('Failed to copy link.', 'danger'));
}

function openImportDialog(sharedFavs) {
    state.modalHistory = [() => closeModal()];
    openModal('Import Shared Favorites', true);
    
    const count = sharedFavs.length;
    dom.modalList.innerHTML = `
        <div style="text-align:center;padding:1.5rem;">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom:1rem;color:var(--accent);">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <h3 style="margin-bottom:0.75rem;font-size:1.25rem;">Import Shared List?</h3>
            <p style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:1.5rem;">
                Someone shared a list of <strong>${count}</strong> favorite titles with you. Would you like to add them to your favorites?
            </p>
            <div style="display:flex;gap:0.75rem;">
                <button class="btn-primary" id="btnImportConfirm" style="flex:1;">IMPORT & MERGE</button>
                <button class="btn-secondary" id="btnImportCancel" style="flex:1;">CANCEL</button>
            </div>
        </div>
    `;
    
    document.getElementById('btnImportCancel').onclick = closeModal;
    document.getElementById('btnImportConfirm').onclick = () => {
        let importedCount = 0;
        sharedFavs.forEach(s => {
            const exists = state.favorites.some(f => f.url === s.u);
            if (!exists) {
                state.favorites.push({
                    source: s.s,
                    type: s.t,
                    name: s.n,
                    url: s.u,
                    thumbnail: s.th
                });
                importedCount++;
            }
        });
        
        if (importedCount > 0) {
            localStorage.setItem(state.storageKey, JSON.stringify(state.favorites));
            renderFavorites();
            showToast(`Successfully imported ${importedCount} new favorites!`);
        } else {
            showToast('All items are already in your favorites list.');
        }
        closeModal();
    };
}

function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    
    const itemCode = params.get('item');
    if (itemCode) {
        const data = decodeShareData(itemCode);
        if (data && data.s && data.t && data.n && data.u) {
            const item = {
                source: data.s,
                type: data.t,
                name: data.n,
                url: data.u
            };
            window.history.replaceState({}, document.title, window.location.pathname);
            state.activeItem = item;
            handleItemClick(item, item.type);
            showToast(`Opening shared title: ${item.name}`);
        }
    }
    
    const favsCode = params.get('favs');
    if (favsCode) {
        const sharedFavs = decodeShareData(favsCode);
        if (Array.isArray(sharedFavs) && sharedFavs.length > 0) {
            window.history.replaceState({}, document.title, window.location.pathname);
            openImportDialog(sharedFavs);
        }
    }
}

// Bind click events
dom.shareModalBtn.onclick = shareActiveItem;
dom.shareFavoritesBtn.onclick = shareFavoritesList;

// Run URL parameter check on launch
setTimeout(checkUrlParams, 500);
