/* IntelliPrep — Main JS v2 */

/* ── Hamburger / mobile sidebar ─────────────────────────────────────────────── */
(function () {
  var btn     = document.getElementById('hamburger-btn');
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebar-overlay');
  if (!btn || !sidebar || !overlay) return;

  function open()  {
    sidebar.classList.add('sidebar-open');
    overlay.classList.add('visible');
    btn.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }
  function close() {
    sidebar.classList.remove('sidebar-open');
    overlay.classList.remove('visible');
    btn.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', function () {
    sidebar.classList.contains('sidebar-open') ? close() : open();
  });
  overlay.addEventListener('click', close);
  sidebar.querySelectorAll('.nav-link, .logout-btn').forEach(function (el) {
    el.addEventListener('click', close);
  });
})();

/* ── Password toggle ─────────────────────────────────────────────────────────── */
document.querySelectorAll('.toggle-pw').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var input = btn.parentElement.querySelector('input');
    if (input) input.type = input.type === 'password' ? 'text' : 'password';
  });
});

/* ── Active nav highlight ────────────────────────────────────────────────────── */
(function () {
  var path = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href && path.startsWith(href) && href !== '/') {
      link.classList.add('active');
    }
  });
})();

/* ── Smooth page-exit transitions on nav clicks ─────────────────────────────── */
document.querySelectorAll('a[href]').forEach(function (a) {
  var href = a.getAttribute('href');
  if (!href || href.startsWith('#') || href.startsWith('http') ||
      a.target === '_blank' || a.hasAttribute('download')) return;

  a.addEventListener('click', function (e) {
    e.preventDefault();
    document.body.style.transition = 'opacity .2s ease';
    document.body.style.opacity = '0';
    setTimeout(function () { window.location.href = href; }, 200);
  });
});

/* ── Option selection ripple + visual feedback ───────────────────────────────── */
document.querySelectorAll('.option-interactive').forEach(function (label) {
  label.addEventListener('click', function () {
    document.querySelectorAll('.option-interactive').forEach(function (l) {
      l.style.transform = '';
    });
  });
});

/* ── Submit button: loading state ────────────────────────────────────────────── */
document.querySelectorAll('form').forEach(function (form) {
  form.addEventListener('submit', function () {
    var btn = form.querySelector('button[type="submit"]');
    if (btn && !btn.disabled) {
      btn.disabled = true;
      var orig = btn.innerHTML;
      btn.innerHTML = '<span style="display:inline-flex;align-items:center;gap:.4rem">'
        + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"'
        + ' style="animation:spin .7s linear infinite">'
        + '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83'
        + 'M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>'
        + 'Processing…</span>';
    }
  });
});

/* ── Animate topic bars on load ──────────────────────────────────────────────── */
(function () {
  var bars = document.querySelectorAll('.topic-bar');
  bars.forEach(function (bar) {
    var target = bar.style.width;
    bar.style.width = '0';
    requestAnimationFrame(function () {
      setTimeout(function () { bar.style.width = target; }, 100);
    });
  });
})();

/* ── Stagger section-card animations ────────────────────────────────────────── */
(function () {
  document.querySelectorAll('.section-card, .stat-card, .calibration-banner').forEach(function (el, i) {
    el.style.animationDelay = (i * 0.07) + 's';
  });
})();
