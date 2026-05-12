document.addEventListener("DOMContentLoaded", function () {

    // =========================
    // SUBMENU TOGGLE (ALL LEVELS)
    // =========================
    document.querySelectorAll('.dropdown-submenu').forEach(function (el) {

        const menu = el.querySelector('.dropdown-menu');
        const toggle = el.querySelector('.dropdown-toggle');

        if (!menu || !toggle) return;

        // CLICK toggle
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            // đóng các submenu cùng cấp (tránh loạn)
            let parentMenu = el.parentElement;
            parentMenu.querySelectorAll(':scope > .dropdown-submenu > .dropdown-menu')
                .forEach(m => {
                    if (m !== menu) m.classList.remove('show');
                });

            menu.classList.toggle('show');
        });

        // HOVER (desktop)
        el.addEventListener('mouseenter', function () {
            menu.classList.add('show');
        });

        el.addEventListener('mouseleave', function () {
            menu.classList.remove('show');
        });

    });

    // =========================
    // CHẶN Bootstrap auto-close phá submenu
    // =========================
    document.querySelectorAll('.dropdown-menu').forEach(function (menu) {
        menu.addEventListener('click', function (e) {
            e.stopPropagation();
        });
    });

});