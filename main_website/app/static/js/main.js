/* IntelliPrep — Main JavaScript */

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
