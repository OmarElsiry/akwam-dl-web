document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.querySelector('.close-modal');

    let currentSource = 'akwam';

    // Tabs
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSource = btn.dataset.source;
            searchInput.placeholder = `Search on ${currentSource === 'akwam' ? 'Akwam' : 'EgyDead'}...`;
        });
    });

    // Search function
    const performSearch = async () => {
        const query = searchInput.value.trim();
        if (!query) return;

        const type = document.querySelector('input[name="search-type"]:checked').value;

        resultsContainer.innerHTML = '<div class="loading-state"><span class="loader"></span><p>Searching for content...</p></div>';

        try {
            const apiPath = currentSource === 'akwam' ? '/api/akwam' : '/api/egydead';
            const response = await fetch(`${apiPath}?action=search&q=${encodeURIComponent(query)}&type=${type}`);
            const data = await response.json();

            renderResults(data);
        } catch (error) {
            resultsContainer.innerHTML = `<div class="initial-state"><p>Error: ${error.message}</p></div>`;
        }
    };

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    const renderResults = (results) => {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = '<div class="initial-state"><p>No results found.</p></div>';
            return;
        }

        resultsContainer.innerHTML = '';
        results.forEach(item => {
            const card = document.createElement('div');
            card.className = 'card';

            // Generate a random-ish placeholder if no image
            const placeholder = currentSource === 'akwam' ?
                `https://picsum.photos/seed/${item.id || item.title}/300/450` :
                (item.image || `https://picsum.photos/seed/${item.title}/300/450`);

            card.innerHTML = `
                <img src="${placeholder}" class="card-img" alt="${item.title}" onerror="this.src='https://via.placeholder.com/300x450/1a1a1e/ffffff?text=${encodeURIComponent(item.title)}'">
                <div class="card-content">
                    <h3 class="card-title">${item.title}</h3>
                    <p class="card-meta">${currentSource.toUpperCase()} • ${item.id || 'Media'}</p>
                </div>
            `;

            card.addEventListener('click', () => showDetails(item));
            resultsContainer.appendChild(card);
        });
    };

    const showDetails = async (item) => {
        modal.style.display = 'block';
        modalBody.innerHTML = '<div class="loading-state"><span class="loader"></span><p>Fetching download links...</p></div>';

        try {
            const apiPath = currentSource === 'akwam' ? '/api/akwam' : '/api/egydead';
            const response = await fetch(`${apiPath}?action=details&url=${encodeURIComponent(item.url)}`);
            const data = await response.json();

            if (currentSource === 'akwam') {
                renderAkwamDetails(item.title, data);
            } else {
                renderEgyDeadDetails(item.title, data);
            }
        } catch (error) {
            modalBody.innerHTML = `<p>Error loading details: ${error.message}</p>`;
        }
    };

    const renderAkwamDetails = (title, qualities) => {
        let html = `<h2>${title}</h2><p>Select quality to extract direct link:</p><div class="quality-grid">`;

        Object.keys(qualities).forEach(q => {
            html += `<button class="link-btn" onclick="resolveAkwam('${qualities[q]}', '${q}')">${q}</button>`;
        });

        html += '</div><div id="resolve-result"></div>';
        modalBody.innerHTML = html;
    };

    const renderEgyDeadDetails = (title, data) => {
        let html = `<h2>${title}</h2>`;

        if (data.episodes && data.episodes.length > 0) {
            html += `<p>Episodes found:</p><div class="episode-grid">`;
            data.episodes.forEach(ep => {
                html += `<button class="link-btn" onclick="loadEgyDetails('${ep.url}', '${ep.title}')">${ep.title}</button>`;
            });
            html += '</div>';
        }

        if (data.links && data.links.length > 0) {
            html += `<p style="margin-top:20px">Download Servers:</p><div class="quality-grid">`;
            data.links.forEach(l => {
                html += `<a href="${l.url}" target="_blank" class="link-btn">
                    <strong>${l.server}</strong><br><small>${l.quality}</small>
                </a>`;
            });
            html += '</div>';
        }

        if (!data.links?.length && !data.episodes?.length) {
            html += '<p>No links or episodes found for this item.</p>';
        }

        modalBody.innerHTML = html;
    };

    // Global listeners for resolve actions (since they are in strings)
    window.resolveAkwam = async (shortUrl, quality) => {
        const resDiv = document.getElementById('resolve-result');
        resDiv.innerHTML = '<p style="margin-top:20px">Resolving direct link... ⏳</p>';

        try {
            const response = await fetch(`/api/akwam?action=resolve&url=${encodeURIComponent(shortUrl)}`);
            const data = await response.json();

            if (data.direct_url) {
                resDiv.innerHTML = `
                    <div style="background:rgba(0,255,0,0.1); padding:20px; border-radius:12px; margin-top:20px; border:1px solid rgba(0,255,0,0.2)">
                        <p style="color:#00ff00; margin-bottom:10px">✔ Direct Link Found (${quality})</p>
                        <a href="${data.direct_url}" class="link-btn" style="background:#00ff00; color:black; display:block">DOWNLOAD NOW</a>
                        <p style="font-size:0.8rem; margin-top:10px; word-break:break-all; opacity:0.6">${data.direct_url}</p>
                    </div>
                `;
            } else {
                resDiv.innerHTML = '<p style="color:#ff4b2b; margin-top:20px">Failed to resolve. The link might be expired.</p>';
            }
        } catch (e) {
            resDiv.innerHTML = `<p style="color:#ff4b2b; margin-top:20px">Error: ${e.message}</p>`;
        }
    };

    window.loadEgyDetails = async (url, title) => {
        modalBody.innerHTML = '<div class="loading-state"><span class="loader"></span><p>Loading episode details...</p></div>';
        try {
            const response = await fetch(`/api/egydead?action=details&url=${encodeURIComponent(url)}`);
            const data = await response.json();
            renderEgyDeadDetails(title, data);
        } catch (e) {
            modalBody.innerHTML = `<p>Error: ${e.message}</p>`;
        }
    };

    // Modal Close
    closeModal.onclick = () => modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == modal) modal.style.display = 'none';
    };
});
