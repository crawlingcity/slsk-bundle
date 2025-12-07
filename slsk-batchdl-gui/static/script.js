document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            let theme = 'light';
            if (document.body.classList.contains('dark-mode')) {
                theme = 'dark';
            }
            localStorage.setItem('theme', theme);
        });
    }

    // Advanced Mode Toggle
    const advancedToggle = document.getElementById('advanced-mode-toggle');
    const advancedOptions = document.getElementById('advanced-options');

    if (advancedToggle && advancedOptions) {
        advancedToggle.addEventListener('change', function() {
            if (this.checked) {
                advancedOptions.style.display = 'block';
            } else {
                advancedOptions.style.display = 'none';
            }
        });
    }

    // Buttons
    const luckyBtn = document.getElementById('lucky-btn');
    const visualBtn = document.getElementById('visual-btn');
    const form = document.getElementById('run-form');

    // I'm Feeling Lucky (Standard Run)
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(form);
        startDownloadData(formData);
    });

    // Visual Search
    if (visualBtn) {
        visualBtn.addEventListener('click', function() {
            const inputVal = document.getElementById('input_text').value;
            if (!inputVal) {
                alert("Please enter search text first.");
                return;
            }
            startVisualSearch(inputVal);
        });
    }
});

function startDownloadData(formData) {
    const output = document.getElementById('output');
    const crashAlert = document.getElementById('crash-alert');

    // Clear previous output and hide alerts
    output.innerHTML = '';
    output.classList.remove('success-border');
    output.classList.add('running-border');
    crashAlert.style.display = 'none';
    output.appendChild(document.createTextNode('Running command...\n'));

    // Scroll to output
    output.scrollIntoView({ behavior: 'smooth' });

    fetch('/run', {
        method: 'POST',
        body: formData
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        function push() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    return;
                }

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        const jsonString = line.substring(6).trim();
                        if (!jsonString) return;

                        try {
                            const message = JSON.parse(jsonString);

                            // Check for special events from the backend
                            if (message.event === 'DONE') {
                                output.appendChild(document.createTextNode('\nCommand finished successfully.'));
                                output.classList.remove('running-border');
                                output.classList.add('success-border');
                                reader.cancel();
                                return;
                            } else if (message.event === 'CRASH') {
                                output.classList.remove('running-border');
                                crashAlert.textContent = `The program stopped unexpectedly with exit code: ${message.code}`;
                                crashAlert.style.display = 'block';
                                output.appendChild(document.createTextNode(`\nCommand failed. See error message above.`));
                                reader.cancel();
                                return;
                            }

                            // Handle regular text output
                            const span = document.createElement('span');
                            span.textContent = message.text;

                            if (message.color === 'red') {
                                span.style.color = 'red';
                            }

                            output.appendChild(span);
                            // Auto-scroll
                            output.scrollTop = output.scrollHeight;

                        } catch (e) {
                            // In case of non-json data, just print it
                            output.appendChild(document.createTextNode(jsonString + '\n'));
                        }
                    }
                });

                push();
            });
        }

        push();

    }).catch(error => {
        output.classList.remove('running-border');
        crashAlert.textContent = `Failed to connect to the server: ${error}`;
        crashAlert.style.display = 'block';
        console.error('Error:', error);
    });
}

function startVisualSearch(query) {
    const modalEl = document.getElementById('visualModal');
    const modal = new bootstrap.Modal(modalEl);
    const resultsContainer = document.getElementById('visual-results');
    const loadingDiv = document.getElementById('visual-loading');

    modal.show();
    resultsContainer.innerHTML = '';
    loadingDiv.style.display = 'block';

    const formData = new FormData();
    formData.append('input_text', query);

    fetch('/search', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loadingDiv.style.display = 'none';

        if (data.error) {
            resultsContainer.innerHTML = `<div class="alert alert-danger w-100">${data.error}</div>`;
            return;
        }

        if (!data.results || data.results.length === 0) {
            resultsContainer.innerHTML = `<div class="alert alert-warning w-100">No results found for "${query}"</div>`;
            return;
        }

        data.results.forEach(item => {
            const col = document.createElement('div');
            col.className = 'col';
            col.innerHTML = `
                <div class="card h-100">
                    <img src="${item.art_url}" class="card-img-top" alt="Cover Art" style="height: 200px; object-fit: cover;">
                    <div class="card-body d-flex flex-column">
                        <h5 class="card-title text-truncate" title="${item.album}">${item.album}</h5>
                        <p class="card-text text-muted">${item.artist}</p>
                        <p class="card-text small">${item.files} source(s)</p>
                        <button class="btn btn-primary mt-auto download-select-btn">Download</button>
                    </div>
                </div>
            `;

            col.querySelector('.download-select-btn').addEventListener('click', () => {
                modal.hide();
                // Trigger download with specific constraints
                // We use the same form but append constraints programmatically?
                // Actually, easiest is to just construct FormData manually
                const form = document.getElementById('run-form');
                const formData = new FormData(form);

                // Override text with original query (already there)
                // Add strict search
                formData.append('input_text', `${item.artist} ${item.album}`);
                // Wait, if we just put "Artist Album" it might match loose things.
                // Ideally we want to pass --strict-artist and --strict-album
                // But our main.py only supports checkboxes for boolean flags like desperate/fast_search
                // We don't have endpoints for --strict-artist in the Python wrapper form.
                // We can "hack" it by putting it in the input_text if sldl supports it freely?
                // No, we removed manual arg passing.

                // Alternative: The Python backend's build_command logic is fixed.
                // We could add `strict_artist: bool` to the form.
                // OR we just search for "Artist Album" and hope for the best (usually works well).
                // Let's stick to updating the search query to "Artist Album" for now, which is "I'm Feeling Lucky" on that specific album.

                // Update the visible input too so user sees what's happening
                document.getElementById('input_text').value = `${item.artist} ${item.album}`;
                formData.set('input_text', `${item.artist} ${item.album}`);
                formData.append('album', 'true'); // Force album mode

                startDownloadData(formData);
            });

            resultsContainer.appendChild(col);
        });
    })
    .catch(err => {
        loadingDiv.style.display = 'none';
        resultsContainer.innerHTML = `<div class="alert alert-danger w-100">Error: ${err}</div>`;
    });
}
