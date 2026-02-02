document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsContainer = document.getElementById('results-container');
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.querySelector('.close-modal');

    // Source Toggle Logic
    const sourceBtns = document.querySelectorAll('.toggle-btn[data-source]');
    let currentSource = 'akwam';

    sourceBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            sourceBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSource = btn.dataset.source;
            searchInput.placeholder = `Search on ${currentSource === 'akwam' ? 'Akwam' : 'EgyDead'}...`;
        });
    });

    // Search
    const performSearch = async () => {
        const query = searchInput.value.trim();
        if (!query) return;

        const typeRadio = document.querySelector('input[name="search-type"]:checked');
        const type = typeRadio ? typeRadio.value : 'movie';

        resultsContainer.innerHTML = '<div class="loading-state" style="grid-column:1/-1; text-align:center"><span class="loader"></span><p style="margin-top:20px; color:var(--text-muted)">Searching...</p></div>';

        try {
            const apiPath = `/api/${currentSource}`;
            const response = await fetch(`${apiPath}?action=search&q=${encodeURIComponent(query)}&type=${type}`);
            const data = await response.json();
            renderResults(data);
        } catch (error) {
            resultsContainer.innerHTML = `<div class="initial-state" style="grid-column:1/-1; text-align:center; color:#ff4b4b"><p>Error: ${error.message}</p></div>`;
        }
    };

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    const renderResults = (results) => {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:50px; color:var(--text-muted)">No results found.</div>';
            return;
        }

        resultsContainer.innerHTML = '';
        results.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'card fade-in';
            card.style.animationDelay = `${index * 50}ms`;

            const placeholder = currentSource === 'akwam' ?
                `https://ui-avatars.com/api/?name=${encodeURIComponent(item.title)}&background=random&size=300` :
                (item.image || `https://ui-avatars.com/api/?name=${encodeURIComponent(item.title)}&background=random&size=300`);

            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img src="${placeholder}" class="card-img" alt="${item.title}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiB2aWV3Qm94PSIwIDAgMjAwIDMwMCI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIzMDAiIGZpbGw9IiMyMjIiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjAiIGZpbGw9IiM1NTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPk5vIEltYWdlPC90ZXh0Pjwvc3ZnPg=='">
                    <div class="card-overlay">
                        <h3 class="card-title">${item.title}</h3>
                        <p class="card-meta">${currentSource.toUpperCase()} • ${item.id || 'Media'}</p>
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
        modalBody.innerHTML = '<div style="text-align:center; padding:50px"><span class="loader"></span><p style="margin-top:20px">Fetching details...</p></div>';

        try {
            const apiPath = `/api/${currentSource}`;

            // Check if it's a series (implies using 'episodes' action for Akwam)
            // 'item' usually contains url directly
            const isSeries = document.querySelector('input[name="search-type"]:checked').value === 'series';

            let data;
            if (currentSource === 'akwam' && isSeries) {
                // Fetch episodes for series
                const res = await fetch(`${apiPath}?action=episodes&url=${encodeURIComponent(item.url)}`);
                data = await res.json();
                renderAkwamSeries(item.title, data, item.url);
            } else {
                // Movie or EgyDead (which handles details differently)
                const res = await fetch(`${apiPath}?action=details&url=${encodeURIComponent(item.url)}`);
                data = await res.json();

                if (currentSource === 'akwam') {
                    renderAkwamMovie(item.title, data);
                } else {
                    renderEgyDeadDetails(item.title, data);
                }
            }

        } catch (error) {
            modalBody.innerHTML = `<p style="color:#ff4b4b">Error: ${error.message}</p>`;
        }
    };

    // --- AKWAM RENDERERS ---

    const renderAkwamMovie = (title, qualities) => {
        let html = `<h2 class="modal-title">${title}</h2><p style="color:var(--text-muted)">Select quality to download:</p><div class="btn-grid">`;
        Object.keys(qualities).forEach(q => {
            let qClass = 'quality-high';
            if (q.includes('720')) qClass = 'quality-med';
            if (q.includes('480')) qClass = 'quality-low';
            html += `<button class="action-btn ${qClass}" onclick="resolveAkwam('${qualities[q]}', '${q}')">${q}</button>`;
        });
        html += '</div><div id="resolve-result"></div>';
        modalBody.innerHTML = html;
    };

    const renderAkwamSeries = (title, episodes, seriesUrl) => {
        // 'episodes' is array of {title, url}
        let html = `<h2 class="modal-title">${title}</h2>`;

        // Batch Download Button
        html += `
            <button id="batch-dl-btn" class="download-all-btn">
                ⚡ DOWNLOAD ALL EPISODES
            </button>
            <div id="batch-progress" style="margin-bottom:20px; display:none"></div>
            <div id="batch-results" style="max-height:300px; overflow-y:auto; margin-bottom:30px; border:1px solid var(--glass-border); border-radius:15px; padding:10px; background:rgba(0,0,0,0.2); display:none"></div>
        `;

        html += `<p style="color:var(--text-muted); margin-bottom:15px">Or select individual episode:</p><div class="btn-grid">`;
        episodes.forEach((ep, idx) => {
            html += `<button class="action-btn" onclick="fetchEpisodeQualities('${ep.url}', '${ep.title}')">Ep ${idx + 1}: ${ep.title}</button>`;
        });
        html += '</div><div id="resolve-result" style="margin-top:30px"></div>';
        modalBody.innerHTML = html;

        // Attach event to Batch Button
        setTimeout(() => {
            const btn = document.getElementById('batch-dl-btn');
            if (btn) btn.onclick = () => startBatchDownload(episodes);
        }, 0);
    };

    // --- BATCH DOWNLOAD LOGIC ---
    window.startBatchDownload = async (episodes) => {
        const btn = document.getElementById('batch-dl-btn');
        const progress = document.getElementById('batch-progress');
        const resultsBox = document.getElementById('batch-results');

        btn.disabled = true;
        btn.innerHTML = '<span class="loader" style="width:20px; height:20px; border-width:2px; vertical-align:middle; margin-right:10px"></span> PROCESSING...';
        progress.style.display = 'block';
        resultsBox.style.display = 'block';

        // Collect all links for bulk copy
        const collectedLinks = [];

        for (let i = 0; i < total; i += CHUNK_SIZE) {
            const chunk = episodes.slice(i, i + CHUNK_SIZE);
            progress.innerHTML = `<p style="color:var(--secondary)">Processing batch ${Math.ceil((i + 1) / CHUNK_SIZE)} of ${Math.ceil(total / CHUNK_SIZE)}... (${completed}/${total} completed)</p>`;

            await Promise.all(chunk.map(async (ep) => {
                try {
                    // 1. Get Qualities
                    const qRes = await fetch(`/api/akwam?action=details&url=${encodeURIComponent(ep.url)}`);
                    const qualities = await qRes.json();

                    if (!qualities || Object.keys(qualities).length === 0) throw new Error("No qualities");

                    // 2. Pick best quality (preference: 720p > 1080p > 480p)
                    const qKeys = Object.keys(qualities);
                    let targetQ = qKeys.find(k => k.includes('720')) || qKeys[0];
                    let downloadPageUrl = qualities[targetQ];

                    // 3. Resolve Direct Link
                    const rRes = await fetch(`/api/akwam?action=resolve&url=${encodeURIComponent(downloadPageUrl)}`);
                    const rData = await rRes.json();

                    if (rData.direct_url) {
                        collectedLinks.push(rData.direct_url);

                        const div = document.createElement('div');
                        div.className = 'result-box fade-in';
                        div.innerHTML = `
                            <div>
                                <strong style="color:var(--secondary)">${ep.title}</strong>
                                <span style="font-size:0.8em; opacity:0.7; margin-left:10px">${targetQ}</span>
                            </div>
                            <a href="${rData.direct_url}" class="action-btn" style="padding:5px 15px; font-size:0.8rem; text-decoration:none">Download</a>
                        `;
                        resultsBox.prepend(div);
                    } else {
                        throw new Error("Resolution failed");
                    }
                } catch (e) {
                    const div = document.createElement('div');
                    div.className = 'result-box fade-in';
                    div.style.borderColor = '#f87171';
                    div.style.background = 'rgba(248, 113, 113, 0.1)';
                    div.innerHTML = `<span style="color:#f87171">Failed: ${ep.title}</span>`;
                    resultsBox.appendChild(div);
                }
                completed++;
            }));

            await new Promise(r => setTimeout(r, 500));
        }

        btn.innerHTML = '✅ DONE';

        // Show Copy Button if links found
        if (collectedLinks.length > 0) {
            progress.innerHTML = `
                <p style="color:#4ade80; margin-bottom:10px">Completed! ${collectedLinks.length} links resolved.</p>
                <button id="copy-all-btn" class="action-btn" style="width:100%; background:var(--primary); color:#000; font-weight:800">
                    📋 COPY ALL LINKS TO CLIPBOARD
                </button>
            `;

            document.getElementById('copy-all-btn').onclick = () => {
                navigator.clipboard.writeText(collectedLinks.join('\n'));
                const cBtn = document.getElementById('copy-all-btn');
                cBtn.innerText = "COPIED!";
                setTimeout(() => cBtn.innerText = "📋 COPY ALL LINKS TO CLIPBOARD", 2000);
            };
        } else {
            progress.innerHTML = `<p style="color:#f87171">Completed, but no links were resolved.</p>`;
        }
    };

    // --- SINGLE EPISODE FLOW (AKWAM) ---
    window.fetchEpisodeQualities = async (url, title) => {
        const resDiv = document.getElementById('resolve-result');
        resDiv.innerHTML = '<div style="text-align:center"><span class="loader"></span></div>';

        const qRes = await fetch(`/api/akwam?action=details&url=${encodeURIComponent(url)}`);
        const qualities = await qRes.json();

        let html = `<h4>${title} - Qualities</h4><div class="btn-grid" style="margin-bottom:20px">`;
        Object.keys(qualities).forEach(q => {
            html += `<button class="action-btn" onclick="resolveAkwam('${qualities[q]}', '${q}')">${q}</button>`;
        });
        html += '</div>';
        resDiv.innerHTML = html;
    };

    // --- EGYDEAD RENDERER ---
    const renderEgyDeadDetails = (title, data) => {
        let html = `<h2 class="modal-title">${title}</h2>`;

        if (data.episodes && data.episodes.length > 0) {
            html += `<p style="color:var(--text-muted)">Episodes Found:</p><div class="btn-grid">`;
            data.episodes.forEach(ep => {
                html += `<button class="action-btn" onclick="loadEgyDetails('${ep.url}', '${ep.title}')">${ep.title}</button>`;
            });
            html += '</div>';
        }

        if (data.links && data.links.length > 0) {
            html += `<p style="margin-top:20px; color:var(--text-muted)">Download Servers:</p><div class="btn-grid">`;
            data.links.forEach((l, i) => {
                html += `<a href="${l.url}" target="_blank" class="action-btn" style="text-align:center; text-decoration:none">
                    <div style="font-size:0.9em">${l.server}</div>
                    <div style="font-size:0.7em; opacity:0.7">${l.quality}</div>
                 </a>`;
            });
            html += '</div>';
        }

        modalBody.innerHTML = html;
    };

    // --- RESOLVERS ---
    window.resolveAkwam = async (url, quality) => {
        const resDiv = document.getElementById('resolve-result');
        // If we are in the single episode view, handle that specific div, otherwise append end of modal
        // Actually for simplicity, we'll just clobber the bottom area or create a popup? 
        // Let's use the 'resolve-result' div we placed in renderAkwamMovie/Series

        if (!resDiv) return;

        resDiv.innerHTML = '<p style="text-align:center; color:var(--secondary)">Resolving link...</p>';
        try {
            const rRes = await fetch(`/api/akwam?action=resolve&url=${encodeURIComponent(url)}`);
            const data = await rRes.json();

            if (data.direct_url) {
                resDiv.innerHTML = `
                    <div class="result-box fade-in" style="background:rgba(79, 172, 254, 0.1); border-color:var(--primary)">
                         <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-right:10px">
                            <span style="color:var(--primary)">✔ DIRECT LINK (${quality})</span><br>
                            <a href="${data.direct_url}" class="card-meta" style="color:#fff; text-decoration:underline">${data.direct_url}</a>
                         </div>
                         <a href="${data.direct_url}" class="action-btn" style="background:var(--secondary); color:#000; padding:10px 20px; text-decoration:none">DOWNLOAD</a>
                    </div>
                 `;
            } else {
                throw new Error("Link broken");
            }
        } catch (e) {
            resDiv.innerHTML = `<p style="color:#f87171; text-align:center">Resolution failed: ${e.message}</p>`;
        }
    };

    window.loadEgyDetails = async (url, title) => {
        // Reuse modal loading state
        modalBody.innerHTML = '<div style="text-align:center; padding:50px"><span class="loader"></span></div>';
        try {
            const response = await fetch(`/api/egydead?action=details&url=${encodeURIComponent(url)}`);
            const data = await response.json();
            renderEgyDeadDetails(title, data);
        } catch (e) {
            modalBody.innerHTML = `<p>Error: ${e.message}</p>`;
        }
    };

    // Closing Logic
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
