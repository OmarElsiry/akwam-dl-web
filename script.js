document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.querySelector('.close-modal');

    // Focus search on load
    searchInput.focus();

    // Search
    const performSearch = async () => {
        const query = searchInput.value.trim();
        if (!query) return;

        const typeRadio = document.querySelector('input[name="search-type"]:checked');
        const type = typeRadio ? typeRadio.value : 'movie';

        resultsContainer.innerHTML = `
            <div class="loading-state" style="grid-column:1/-1; text-align:center">
                <span class="loader"></span>
                <p style="margin-top:20px; color:var(--text-muted)">Searching...</p>
            </div>`;

        try {
            // Only using Akwam API
            const response = await fetch(`/api/akwam?action=search&q=${encodeURIComponent(query)}&type=${type}`);
            const data = await response.json();
            renderResults(data);
        } catch (error) {
            resultsContainer.innerHTML = `
                <div class="initial-state" style="grid-column:1/-1; text-align:center; color:#ff4b4b; padding: 50px;">
                    <p>Connection Error</p>
                    <small style="opacity:0.7">${error.message}</small>
                </div>`;
        }
    };

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    const renderResults = (results) => {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = `
                <div style="grid-column:1/-1; text-align:center; padding:100px; color:var(--text-muted)">
                    <p style="font-size:1.2rem; margin-bottom:10px">No results found</p>
                    <p style="font-size:0.9rem; opacity:0.6">Try a different keyword</p>
                </div>`;
            return;
        }

        resultsContainer.innerHTML = '';
        results.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'card fade-in';
            card.style.animationDelay = `${index * 50}ms`;

            const placeholder = `https://ui-avatars.com/api/?name=${encodeURIComponent(item.title)}&background=random&size=300`;

            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img src="${placeholder}" class="card-img" alt="${item.title}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiB2aWV3Qm94PSIwIDAgMjAwIDMwMCI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIzMDAiIGZpbGw9IiMyMjIiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjAiIGZpbGw9IiM1NTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPk5vIEltYWdlPC90ZXh0Pjwvc3ZnPg=='">
                    <div class="card-overlay">
                        <h3 class="card-title">${item.title}</h3>
                        <p class="card-meta">AKWAM • ${item.id || 'Media'}</p>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => showDetails(item));
            resultsContainer.appendChild(card);
        });
    };

    const showDetails = async (item) => {
        modal.classList.add('show');
        modal.style.display = 'block';
        modalBody.innerHTML = `
            <div style="text-align:center; padding:100px 0;">
                <span class="loader"></span>
                <p style="margin-top:20px; color:var(--text-muted)">Fetching details...</p>
            </div>`;

        try {
            const isSeries = document.querySelector('input[name="search-type"]:checked').value === 'series';

            let data;
            if (isSeries) {
                // Fetch episodes for series
                const res = await fetch(`/api/akwam?action=episodes&url=${encodeURIComponent(item.url)}`);
                data = await res.json();
                renderSeries(item.title, data, item.url);
            } else {
                // Movie
                const res = await fetch(`/api/akwam?action=details&url=${encodeURIComponent(item.url)}`);
                data = await res.json();
                renderMovie(item.title, data);
            }

        } catch (error) {
            modalBody.innerHTML = `<p style="color:#ff4b4b; text-align:center; padding:50px;">Error: ${error.message}</p>`;
        }
    };

    // --- RENDERERS ---

    const renderMovie = (title, qualities) => {
        let html = `<h2 class="modal-title">${title}</h2><p style="color:var(--text-muted); margin-bottom:20px">Select quality:</p><div class="btn-grid">`;
        Object.keys(qualities).forEach(q => {
            let qClass = 'quality-high';
            if (q.includes('720')) qClass = 'quality-med';
            if (q.includes('480')) qClass = 'quality-low';
            html += `<button class="action-btn ${qClass}" onclick="resolveLink('${qualities[q]}', '${q}')">${q}</button>`;
        });
        html += '</div><div id="resolve-result"></div>';
        modalBody.innerHTML = html;
    };

    const renderSeries = (title, episodes, seriesUrl) => {
        let html = `<h2 class="modal-title">${title}</h2>`;

        // Batch Download Button
        html += `
            <div class="batch-section">
                <button id="batch-dl-btn" class="download-all-btn">
                    <span class="icon">⚡</span> DOWNLOAD ALL EPISODES
                </button>
                <div id="batch-progress" style="display:none; margin-bottom: 20px;"></div>
                <div id="batch-results" class="batch-results-container" style="display:none;"></div>
            </div>
        `;

        html += `<p style="color:var(--text-muted); margin-bottom:15px; font-weight:500;">Individual Episodes:</p><div class="btn-grid">`;
        episodes.forEach((ep, idx) => {
            html += `<button class="action-btn" onclick="fetchEpisodeQualities('${ep.url}', '${ep.title}')">
                <span style="opacity:0.5; font-size:0.8em; display:block">EP ${idx + 1}</span>
                ${ep.title}
             </button>`;
        });
        html += '</div><div id="resolve-result" style="margin-top:30px"></div>';
        modalBody.innerHTML = html;

        setTimeout(() => {
            const btn = document.getElementById('batch-dl-btn');
            if (btn) btn.onclick = () => startBatchDownload(episodes);
        }, 0);
    };

    // --- BATCH PROCESSOR ---
    window.startBatchDownload = async (episodes) => {
        const btn = document.getElementById('batch-dl-btn');
        const progress = document.getElementById('batch-progress');
        const resultsBox = document.getElementById('batch-results');

        btn.disabled = true;
        btn.innerHTML = '<span class="loader" style="width:20px; height:20px; border-width:2px; vertical-align:middle; margin-right:10px"></span> PROCESSING...';
        progress.style.display = 'block';
        resultsBox.style.display = 'block';

        const collectedLinks = [];
        let completed = 0;
        const total = episodes.length;
        const CHUNK_SIZE = 3;

        for (let i = 0; i < total; i += CHUNK_SIZE) {
            const chunk = episodes.slice(i, i + CHUNK_SIZE);
            const currentBatch = Math.ceil((i + 1) / CHUNK_SIZE);
            const totalBatches = Math.ceil(total / CHUNK_SIZE);

            // Progress Bar UI
            const percent = Math.round((completed / total) * 100);
            progress.innerHTML = `
                <div style="display:flex; justify-content:space-between; margin-bottom:5px; font-size:0.9rem; color:var(--text-muted)">
                    <span>Batch ${currentBatch}/${totalBatches}</span>
                    <span>${percent}%</span>
                </div>
                <div style="height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden">
                    <div style="height:100%; width:${percent}%; background:var(--secondary); transition:width 0.3s ease"></div>
                </div>
            `;

            await Promise.all(chunk.map(async (ep) => {
                try {
                    const qRes = await fetch(`/api/akwam?action=details&url=${encodeURIComponent(ep.url)}`);
                    const qualities = await qRes.json();

                    if (!qualities || Object.keys(qualities).length === 0) throw new Error("No qualities");

                    const qKeys = Object.keys(qualities);
                    let targetQ = qKeys.find(k => k.includes('720')) || qKeys[0];
                    let downloadPageUrl = qualities[targetQ];

                    const rRes = await fetch(`/api/akwam?action=resolve&url=${encodeURIComponent(downloadPageUrl)}`);
                    const rData = await rRes.json();

                    if (rData.direct_url) {
                        collectedLinks.push(rData.direct_url);

                        const div = document.createElement('div');
                        div.className = 'result-row fade-in';
                        div.innerHTML = `
                            <div class="row-info">
                                <span class="row-title">${ep.title}</span>
                                <span class="row-badge">${targetQ}</span>
                            </div>
                            <a href="${rData.direct_url}" class="row-btn">Download</a>
                        `;
                        resultsBox.prepend(div);
                    } else {
                        throw new Error("Resolution failed");
                    }
                } catch (e) {
                    const div = document.createElement('div');
                    div.className = 'result-row fade-in error';
                    div.innerHTML = `
                        <div class="row-info">
                            <span class="row-title">${ep.title}</span>
                        </div>
                        <span class="row-status">Failed</span>
                    `;
                    resultsBox.appendChild(div);
                }
                completed++;
            }));

            await new Promise(r => setTimeout(r, 500));
        }

        btn.innerHTML = '✅ COMPLETED';
        btn.classList.add('success');

        if (collectedLinks.length > 0) {
            progress.innerHTML = `
                <div style="background:rgba(74, 222, 128, 0.1); border:1px solid rgba(74, 222, 128, 0.2); padding:15px; border-radius:12px; margin-top:15px;">
                    <p style="color:#4ade80; font-weight:600; margin-bottom:10px">🎉 ${collectedLinks.length} Links Ready</p>
                    <button id="copy-all-btn" class="action-btn" style="width:100%; background:var(--primary); color:#000; font-weight:800; border:none">
                        📋 COPY ALL LINKS
                    </button>
                </div>
            `;

            document.getElementById('copy-all-btn').onclick = function () {
                navigator.clipboard.writeText(collectedLinks.join('\n'));
                this.innerText = "✅ COPIED TO CLIPBOARD!";
                this.style.background = "#4ade80";
                setTimeout(() => {
                    this.innerText = "📋 COPY ALL LINKS";
                    this.style.background = "var(--primary)";
                }, 2000);
            };
        } else {
            progress.innerHTML = `<p style="color:#f87171; text-align:center; margin-top:10px">No valid links were found.</p>`;
        }
    };

    // --- INDIVIDUAL ACTIONS ---
    window.fetchEpisodeQualities = async (url, title) => {
        const resDiv = document.getElementById('resolve-result');
        resDiv.innerHTML = '<div style="text-align:center"><span class="loader"></span></div>';

        const qRes = await fetch(`/api/akwam?action=details&url=${encodeURIComponent(url)}`);
        const qualities = await qRes.json();

        let html = `<h4>${title}</h4><div class="btn-grid" style="margin-bottom:20px">`;
        Object.keys(qualities).forEach(q => {
            html += `<button class="action-btn" onclick="resolveLink('${qualities[q]}', '${q}')">${q}</button>`;
        });
        html += '</div>';
        resDiv.innerHTML = html;
    };

    window.resolveLink = async (url, quality) => {
        const resDiv = document.getElementById('resolve-result');
        if (!resDiv) return;

        resDiv.innerHTML = '<p style="text-align:center; color:var(--secondary); animation: pulse 1s infinite">Resolving...</p>';
        try {
            const rRes = await fetch(`/api/akwam?action=resolve&url=${encodeURIComponent(url)}`);
            const data = await rRes.json();

            if (data.direct_url) {
                resDiv.innerHTML = `
                    <div class="result-box fade-in success-box">
                         <div class="box-content">
                            <span class="success-label">READY TO DOWNLOAD</span>
                            <div class="url-display">${data.direct_url}</div>
                         </div>
                         <a href="${data.direct_url}" class="dl-action-btn">Download Now</a>
                    </div>
                 `;
            } else {
                throw new Error("Link unavailable");
            }
        } catch (e) {
            resDiv.innerHTML = `<p style="color:#f87171; text-align:center">Error: ${e.message}</p>`;
        }
    };

    // Close Modal Logic
    closeModal.onclick = () => {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    };

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }
    };
});
