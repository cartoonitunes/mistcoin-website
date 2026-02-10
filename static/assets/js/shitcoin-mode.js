/**
 * Shitcoin Mode Toggle
 * "Mist" means "shit" in German — MistCoin is technically the first shitcoin.
 */
(function() {
  'use strict';

  var STORAGE_KEY = 'mistcoin_shitcoin_mode';

  function isActive() {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  }

  function applyShitcoinMode(active) {
    var els = document.querySelectorAll('[data-sc]');
    els.forEach(function(el) {
      if (active) {
        if (!el.hasAttribute('data-sc-original')) {
          el.setAttribute('data-sc-original',
            el.hasAttribute('data-sc-html') ? el.innerHTML : el.textContent
          );
        }
        if (el.hasAttribute('data-sc-html')) {
          el.innerHTML = el.getAttribute('data-sc');
        } else {
          el.textContent = el.getAttribute('data-sc');
        }
      } else if (el.hasAttribute('data-sc-original')) {
        if (el.hasAttribute('data-sc-html')) {
          el.innerHTML = el.getAttribute('data-sc-original');
        } else {
          el.textContent = el.getAttribute('data-sc-original');
        }
      }
    });

    // Page title
    if (active) {
      if (!document._scOriginalTitle) document._scOriginalTitle = document.title;
      document.title = document.title
        .replace(/MistCoin/g, 'ShitCoin')
        .replace(/Mist Browser/g, 'Shit Browser')
        .replace(/Mist Simulator/g, 'Shit Simulator');
    } else if (document._scOriginalTitle) {
      document.title = document._scOriginalTitle;
    }
  }

  // --- Poop Rain ---
  function createPoopRain() {
    removePoopRain();
    var container = document.createElement('div');
    container.id = 'poop-rain';
    document.body.appendChild(container);
    var count = 18;
    for (var i = 0; i < count; i++) {
      var poop = document.createElement('div');
      poop.className = 'poop-drop';
      poop.textContent = '\uD83D\uDCA9';
      poop.style.left = (Math.random() * 100) + '%';
      poop.style.animationDuration = (4 + Math.random() * 5) + 's';
      poop.style.animationDelay = (Math.random() * 6) + 's';
      poop.style.fontSize = (16 + Math.random() * 18) + 'px';
      poop.style.opacity = (0.3 + Math.random() * 0.4).toFixed(2);
      container.appendChild(poop);
    }
  }

  function removePoopRain() {
    var existing = document.getElementById('poop-rain');
    if (existing) existing.remove();
  }

  // --- Explosion Animation ---
  function triggerExplosion(btn) {
    var rect = btn.getBoundingClientRect();
    var cx = rect.left + rect.width / 2;
    var cy = rect.top + rect.height / 2;
    var count = 10;
    for (var i = 0; i < count; i++) {
      var particle = document.createElement('div');
      particle.className = 'poop-particle';
      particle.textContent = '\uD83D\uDCA9';
      var angle = (Math.PI * 2 * i) / count;
      var dist = 40 + Math.random() * 40;
      particle.style.setProperty('--tx', Math.cos(angle) * dist + 'px');
      particle.style.setProperty('--ty', Math.sin(angle) * dist + 'px');
      particle.style.left = cx + 'px';
      particle.style.top = cy + 'px';
      particle.style.fontSize = (12 + Math.random() * 10) + 'px';
      document.body.appendChild(particle);
      particle.addEventListener('animationend', function() { this.remove(); });
    }
  }

  // --- URL Sync ---
  function syncURL(active) {
    var url = new URL(window.location.href);
    if (active) {
      url.searchParams.set('shitcoin', 'true');
    } else {
      url.searchParams.delete('shitcoin');
    }
    history.replaceState(null, '', url.toString());
  }

  function toggleShitcoinMode() {
    var nowActive = !document.body.classList.contains('shitcoin-mode');
    document.body.classList.toggle('shitcoin-mode');
    document.documentElement.classList.toggle('shitcoin-mode');
    localStorage.setItem(STORAGE_KEY, nowActive ? 'true' : 'false');
    applyShitcoinMode(nowActive);
    syncURL(nowActive);

    // Poop rain
    if (nowActive) {
      createPoopRain();
    } else {
      removePoopRain();
    }

    // Explosion on toggle ON
    var btn = document.getElementById('shitcoin-toggle');
    if (nowActive && btn) {
      triggerExplosion(btn);
    }

    // Update share button visibility
    var shareBtn = document.getElementById('shitcoin-share');
    if (shareBtn) {
      shareBtn.style.display = nowActive ? 'inline-flex' : 'none';
    }
  }

  function initShareButton() {
    var shareBtn = document.getElementById('shitcoin-share');
    if (!shareBtn) return;
    shareBtn.addEventListener('click', function(e) {
      e.preventDefault();
      var url = new URL(window.location.href);
      url.searchParams.set('shitcoin', 'true');
      navigator.clipboard.writeText(url.toString()).then(function() {
        var original = shareBtn.innerHTML;
        shareBtn.innerHTML = '<span style="font-size:13px;">Copied! \uD83D\uDCA9</span>';
        setTimeout(function() { shareBtn.innerHTML = original; }, 2000);
      });
    });
    shareBtn.style.display = isActive() ? 'inline-flex' : 'none';
  }

  function init() {
    var btn = document.getElementById('shitcoin-toggle');
    if (btn) btn.addEventListener('click', toggleShitcoinMode);

    var active = isActive();
    if (active) {
      document.body.classList.add('shitcoin-mode');
      createPoopRain();
      syncURL(true);
    }
    applyShitcoinMode(active);
    initShareButton();
  }

  // For origin checker AJAX re-apply
  window.reapplyShitcoinMode = function() {
    if (isActive()) applyShitcoinMode(true);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
