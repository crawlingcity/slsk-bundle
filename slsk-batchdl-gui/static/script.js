
document.getElementById('run-form').addEventListener('submit', function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const output = document.getElementById('output');
    const crashAlert = document.getElementById('crash-alert');

    // Clear previous output and hide alerts
    output.innerHTML = ''; 
    crashAlert.style.display = 'none';
    output.appendChild(document.createTextNode('Running command...\n'));

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
                                reader.cancel();
                                return;
                            } else if (message.event === 'CRASH') {
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
        crashAlert.textContent = `Failed to connect to the server: ${error}`;
        crashAlert.style.display = 'block';
        console.error('Error:', error);
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        let theme = 'light';
        if (document.body.classList.contains('dark-mode')) {
            theme = 'dark';
        }
        localStorage.setItem('theme', theme);
    });
});
