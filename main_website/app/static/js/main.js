/* IntelliPrep — Main JavaScript */

// ── Hamburger / mobile sidebar ────────────────────────────────────────────────
(function () {
    var btn     = document.getElementById('hamburger-btn');
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebar-overlay');

    if (!btn || !sidebar || !overlay) return;

    function openSidebar() {
        sidebar.classList.add('sidebar-open');
        overlay.classList.add('visible');
        btn.classList.add('open');
        btn.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        sidebar.classList.remove('sidebar-open');
        overlay.classList.remove('visible');
        btn.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    }

    btn.addEventListener('click', function () {
        sidebar.classList.contains('sidebar-open') ? closeSidebar() : openSidebar();
    });

    overlay.addEventListener('click', closeSidebar);

    // Close on nav link click (mobile)
    sidebar.querySelectorAll('.nav-link, .logout-btn').forEach(function (el) {
        el.addEventListener('click', closeSidebar);
    });
})();

// ── Password toggle ───────────────────────────────────────────────────────────
document.querySelectorAll('.toggle-pw').forEach(function (btn) {
    btn.addEventListener('click', function () {
        var input = btn.parentElement.querySelector('input');
        if (input) {
            input.type = input.type === 'password' ? 'text' : 'password';
        }
    });
});

// ── Active nav link highlight ─────────────────────────────────────────────────
(function () {
    var path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(function (link) {
        var href = link.getAttribute('href');
        if (href && path.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });
})();

// ── Option selection feedback ────────────────────────────────────────────────
document.querySelectorAll('.option-interactive').forEach(function (label) {
    label.addEventListener('click', function () {
        document.querySelectorAll('.option-interactive').forEach(function (l) {
            l.style.borderColor = '';
            l.style.background = '';
        });
    });
});

// ── Auto-submit prevention (double click) ────────────────────────────────────
document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
        var btn = form.querySelector('button[type="submit"]');
        if (btn) {
            btn.disabled = true;
            btn.textContent = btn.textContent + '…';
        }
    });
});

// ── Animate topic bars on load ────────────────────────────────────────────────
(function () {
    var bars = document.querySelectorAll('.topic-bar');
    bars.forEach(function (bar) {
        var target = bar.style.width;
        bar.style.width = '0';
        requestAnimationFrame(function () {
            setTimeout(function () { bar.style.width = target; }, 80);
        });
    });
})();
