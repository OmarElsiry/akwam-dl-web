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
            <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 50px;">
                <p>No results found for your search.</p>
                <small style="opacity:0.5">Try checking the spelling or using a different keyword</small>
            </div>`;
            return;
        }

        resultsContainer.innerHTML = '';
        results.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'card text-only fade-in'; // text-only class for specific styling
            card.style.animationDelay = `${index * 50}ms`;

            // Extract ID for display (visual flair)
            const idMatch = item.url.match(/\/(\d+)\//);
            const displayId = idMatch ? `#${idMatch[1]}` : 'MEDIA';

            // Clean title
            const title = item.title.trim();

            card.innerHTML = `
                <div class="card-content">
                    <div class="card-header-row">
                        <div class="card-icon">🎬</div>
                        <span class="card-id">${displayId}</span>
                    </div>
                    <h3 class="card-title">${title}</h3>
                    <button class="view-btn">View Details</button>
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
            const escapedTitle = ep.title.replace(/'/g, "\\'");
            html += `<button class="action-btn" onclick="fetchEpisodeQualities('${ep.url}', '${escapedTitle}')">
                <span style="opacity:0.5; font-size:0.8em; display:block">EP ${idx + 1}</span>
                ${ep.title}
             </button>`;
        });
        html += '</div><div id="resolve-result" style="margin-top:30px"></div>';
        modalBody.innerHTML = html;

        // Attach event listener immediately
        const btn = document.getElementById('batch-dl-btn');
        if (btn) {
            btn.onclick = (e) => {
                e.preventDefault();
                startBatchDownload(seriesUrl); // High-speed backend batching
            };
        }
    };

    // --- BATCH PROCESSOR (BACKEND DRIVEN - HIGH SPEED) ---
    window.startBatchDownload = async (seriesUrl) => {
        const btn = document.getElementById('batch-dl-btn');
        const progress = document.getElementById('batch-progress');
        const resultsBox = document.getElementById('batch-results');

        if (!btn || !progress || !resultsBox) return;

        btn.disabled = true;
        btn.classList.add('btn-processing');
        btn.innerHTML = '<span class="loader" style="width:16px; height:16px; border-width:2px; vertical-align:middle; margin-right:8px"></span> RESOLVING ENTIRE SEASON...';

        progress.style.display = 'block';
        progress.innerHTML = `
            <div style="text-align:center; padding: 10px;">
                <p style="color:var(--text-secondary); margin-bottom:12px; font-size:0.9rem;">
                    Parallel resolving started... and should finish in 5-10s
                </p>
                <div style="height:6px; background:rgba(255,255,255,0.05); border-radius:3px; overflow:hidden; border: 1px solid var(--border-subtle)">
                    <div class="progress-bar-shimmer" style="height:100%; width:100%; background:var(--accent); opacity:0.6;"></div>
                </div>
            </div>
        `;

        resultsBox.style.display = 'block';
        resultsBox.innerHTML = '';

        try {
            const res = await fetch(`/api/akwam?action=batch&url=${encodeURIComponent(seriesUrl)}`);
            const data = await res.json();

            if (!data || data.length === 0) throw new Error("No links could be resolved.");

            const collectedLinks = [];
            data.forEach(item => {
                collectedLinks.push(item.url);
                const div = document.createElement('div');
                div.className = 'result-row fade-in';
                div.innerHTML = `
                    <div class="row-info">
                        <span class="row-title">${item.title}</span>
                        <span class="row-badge">${item.quality}</span>
                    </div>
                    <a href="${item.url}" target="_blank" class="row-btn">Download</a>
                `;
                resultsBox.appendChild(div);
            });

            btn.innerHTML = '✅ COMPLETED';
            btn.classList.remove('btn-processing');
            btn.classList.add('success');

            progress.innerHTML = `
                <div style="background:rgba(74, 222, 128, 0.1); border:1px solid rgba(74, 222, 128, 0.2); padding:15px; border-radius:12px; margin-top:15px;">
                    <p style="color:#4ade80; font-weight:600; margin-bottom:10px">🎉 Resolved ${collectedLinks.length} Episodes</p>
                    <button id="copy-all-btn" class="action-btn" style="width:100%; background:var(--primary); color:#000; font-weight:800; border:none">
                        📋 COPY ALL LINKS
                    </button>
                </div>
            `;

            document.getElementById('copy-all-btn').onclick = function () {
                navigator.clipboard.writeText(collectedLinks.join('\n'));
                this.innerText = "✅ COPIED!";
                setTimeout(() => { this.innerText = "📋 COPY ALL LINKS"; }, 2000);
            };

        } catch (error) {
            btn.innerHTML = '❌ FAILED';
            btn.disabled = false;
            btn.classList.remove('btn-processing');
            progress.innerHTML = `<p style="color:#f87171; text-align:center; margin-top:10px">Error: ${error.message}</p>`;
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

        resDiv.innerHTML = '<p style="text-align:center; color:var(--accent); animation: btn-pulse 1.5s infinite">Resolving download link...</p>';
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
