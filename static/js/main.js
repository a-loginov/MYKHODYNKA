document.addEventListener('DOMContentLoaded', function () {
    // ── Нижняя навигация: подсветка активного пункта ──
    var path = window.location.pathname;
    var active = null;
    if (path === '/' || path === '/dashboard') active = 'home';
    else if (path.indexOf('/requests') === 0) active = 'requests';
    else if (path.indexOf('/passes') === 0) active = 'passes';
    else if (path.indexOf('/messages') === 0) active = 'messages';

    if (active) {
        document.querySelectorAll('.bottom-nav__item').forEach(function (item) {
            if (item.getAttribute('data-nav') === active) item.classList.add('is-active');
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
