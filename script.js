document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');
    const toggleBtns = document.querySelectorAll('.toggle-btn');
    const modal = document.getElementById('modal');
    const closeModal = document.querySelector('.close-modal');
    const modalBody = document.getElementById('modal-body');

    let currentType = 'movie';
    let currentSource = 'akwam';

    // Handle Type Selection (Movies/Series)
    document.querySelectorAll('input[name="search-type"]').forEach(input => {
        input.addEventListener('change', (e) => {
            currentType = e.target.value;
        });
    });

    // Handle Source Selection (Akwam/EgyDead) - Currently Akwam primary
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.tagName === 'BUTTON') {
                toggleBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentSource = btn.getAttribute('data-source');
            }
        });
    });

    const showLoader = () => {
        resultsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 100px;"><div class="loader"></div></div>';
    };

    const performSearch = async () => {
        const query = searchInput.value.trim();
        if (!query) return;

        showLoader();

        try {
            const resp = await fetch(`/api/akwam?action=search&q=${encodeURIComponent(query)}&type=${currentType}`);
            const data = await resp.json();

            if (!data || data.length === 0) {
                resultsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 50px;">No results found.</div>';
                return;
            }

            renderResults(data);
        } catch (err) {
            resultsContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--accent); padding: 50px;">Error: ${err.message}</div>`;
        }
    };

    const renderResults = (results) => {
        resultsContainer.innerHTML = '';
        results.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'card fade-in';
            card.style.animationDelay = `${index * 0.05}s`;

            // Generate a random placeholder image if no poster available
            const posterUrl = `https://picsum.photos/seed/${item.title}/400/600`;

            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img src="${posterUrl}" alt="${item.title}" class="card-img" loading="lazy">
                    <div class="card-overlay">
                        <h3 class="card-title">${item.title}</h3>
                        <div class="card-meta">${currentType.toUpperCase()}</div>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => showDetails(item));
            resultsContainer.appendChild(card);
        });
    };

    const showDetails = async (item) => {
        modalBody.innerHTML = '<div style="text-align: center; padding: 50px;"><div class="loader"></div></div>';
        modal.style.display = 'block';
        setTimeout(() => modal.classList.add('show'), 10);

        try {
            const action = currentType === 'movie' ? 'details' : 'episodes';
            const resp = await fetch(`/api/akwam?action=${action}&url=${encodeURIComponent(item.url)}`);
            const data = await resp.json();

            if (currentType === 'movie') {
                renderMovieDetails(item, data);
            } else {
                renderSeriesDetails(item, data);
            }
        } catch (err) {
            modalBody.innerHTML = `<div style="color: var(--accent);">Failed to load details: ${err.message}</div>`;
        }
    };

    const renderMovieDetails = (item, qualities) => {
        let qualityBtns = '';
        Object.entries(qualities).forEach(([q, url]) => {
            qualityBtns += `<button class="action-btn quality-${q.includes('1080') ? 'high' : 'med'}" onclick="resolveFinal('${url}', '${q}')">${q}</button>`;
        });

        modalBody.innerHTML = `
            <h2 class="modal-title">${item.title}</h2>
            <div style="margin-bottom: 20px; color: var(--text-muted);">Select Quality to Download:</div>
            <div class="btn-grid">${qualityBtns}</div>
            <div id="resolution-result"></div>
        `;
    };

    const renderSeriesDetails = (item, episodes) => {
        let epBtns = '';
        episodes.forEach(ep => {
            epBtns += `<button class="action-btn" onclick="showEpisodeQualities('${ep.url}', '${ep.title}')">${ep.title}</button>`;
        });

        modalBody.innerHTML = `
            <h2 class="modal-title">${item.title}</h2>
            <div style="margin-bottom: 20px; color: var(--text-muted);">Select Episode:</div>
            <div class="btn-grid">${epBtns}</div>
            <div id="resolution-result"></div>
        `;
    };

    // Global helper for resolving links
    window.resolveFinal = async (url, q) => {
        const resultContainer = document.getElementById('resolution-result');
        resultContainer.innerHTML = '<div style="margin-top: 20px;"><div class="loader" style="width:24px; height:24px;"></div> Resolving link...</div>';

        try {
            const resp = await fetch(`/api/akwam?action=resolve&url=${encodeURIComponent(url)}`);
            const data = await resp.json();

            if (data.direct_url) {
                resultContainer.innerHTML = `
                    <div class="result-box fade-in">
                        <span style="font-weight: 600;">${q || 'Direct'} Link Ready</span>
                        <a href="${data.direct_url}" target="_blank" class="copy-btn" 
                           style="background: var(--primary); color: #000; text-decoration: none; font-weight: 800;">
                           DOWNLOAD NOW
                        </a>
                    </div>
                `;
            } else {
                resultContainer.innerHTML = '<div style="margin-top: 20px; color: var(--accent);">Failed to resolve direct link.</div>';
            }
        } catch (err) {
            resultContainer.innerHTML = `<div style="margin-top: 20px; color: var(--accent);">Error: ${err.message}</div>`;
        }
    };

    window.showEpisodeQualities = async (url, title) => {
        const resultContainer = document.getElementById('resolution-result');
        resultContainer.innerHTML = '<div style="margin-top: 20px;"><div class="loader" style="width:24px; height:24px;"></div> Fetching qualities...</div>';

        try {
            const resp = await fetch(`/api/akwam?action=details&url=${encodeURIComponent(url)}`);
            const qualities = await resp.json();

            let qualityBtns = `<h3 style="margin-top: 25px; margin-bottom: 15px;">${title}</h3><div class="btn-grid">`;
            Object.entries(qualities).forEach(([q, qUrl]) => {
                qualityBtns += `<button class="action-btn quality-${q.includes('1080') ? 'high' : 'med'}" onclick="resolveFinal('${qUrl}', '${q}')">${q}</button>`;
            });
            qualityBtns += '</div>';

            resultContainer.innerHTML = qualityBtns;
        } catch (err) {
            resultContainer.innerHTML = `<div style="margin-top: 20px; color: var(--accent);">Error: ${err.message}</div>`;
        }
    };

    // Event Listeners
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    closeModal.addEventListener('click', () => {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    });

    window.onclick = (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }
    };
});
