document.addEventListener('DOMContentLoaded', function () {
    // ── PWA: регистрация service worker ──
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/static/sw.js').catch(function (err) {
                console.warn('SW registration failed:', err);
            });
        });
    }

    // ── Инфо-триггер (bottom sheet) ──
    var trigger = document.getElementById('infoTrigger');
    var sheet = document.getElementById('bottomSheet');
    var overlay = document.getElementById('overlay');

    if (!trigger || !sheet || !overlay) return;

    function open() {
        sheet.classList.add('open');
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function close() {
        sheet.classList.remove('open');
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    }

    trigger.addEventListener('click', open);
    overlay.addEventListener('click', close);
});
