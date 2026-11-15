/**
 * HEADER INTERACTIONS MODULE
 * Handles header scroll effects, navigation state, and menu interactions
 */

const HeaderModule = (() => {
  const config = {
    scrollThreshold: 50,
    transitionSpeed: 300,
  };

  /**
   * Initialize header scroll effects
   */
  function initScrollEffect() {
    const header = document.querySelector('header');
    if (!header) return;

    let ticking = false;

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          
          if (scrollY > config.scrollThreshold) {
            header.classList.add('scrolled');
          } else {
            header.classList.remove('scrolled');
          }
          
          ticking = false;
        });

        ticking = true;
      }
    }, { passive: true });
  }

  /**
   * Initialize active nav state based on current page
   */
  function initNavState() {
    const navItems = document.querySelectorAll('.nav-item');
    const currentPage = window.location.pathname.split('/').pop() || 'alt_home.html';

    navItems.forEach(item => {
      const href = item.getAttribute('href');
      if (href && href === currentPage) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }

  /**
   * Initialize search functionality
   */
  function initSearch() {
    const searchInput = document.querySelector('.global-search input');
    if (!searchInput) return;

    let searchTimeout;

    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      const query = e.target.value.toLowerCase();

      searchTimeout = setTimeout(() => {
        if (query.length > 0) {
          performSearch(query);
        } else {
          clearSearchHighlight();
        }
      }, 300);
    });

    searchInput.addEventListener('focus', () => {
      // No glow effect - transparent header
    });

    searchInput.addEventListener('blur', () => {
      // No glow effect - transparent header
    });
  }

  /**
   * Perform search across page content
   */
  function performSearch(query) {
    const cards = document.querySelectorAll('[class*="card"], h2, h3, .pill');
    
    cards.forEach(card => {
      const text = card.textContent.toLowerCase();
      if (text.includes(query)) {
        card.style.opacity = '1';
        card.style.pointerEvents = 'auto';
      } else {
        card.style.opacity = '0.3';
        card.style.pointerEvents = 'none';
      }
    });
  }

  /**
   * Clear search highlighting
   */
  function clearSearchHighlight() {
    const cards = document.querySelectorAll('[class*="card"], h2, h3, .pill');
    cards.forEach(card => {
      card.style.opacity = '1';
      card.style.pointerEvents = 'auto';
    });
  }

  /**
   * Initialize skip to main content link
   */
  function initAccessibility() {
    // Create skip link if not present
    if (!document.querySelector('.skip-link')) {
      const skipLink = document.createElement('a');
      skipLink.href = '#main';
      skipLink.textContent = 'Skip to main content';
      skipLink.style.cssText = `
        position: absolute;
        top: -40px;
        left: 0;
        background: var(--thm-base);
        color: #000;
        padding: 8px;
        text-decoration: none;
        z-index: 100;
      `;
      
      skipLink.addEventListener('focus', () => {
        skipLink.style.top = '0';
      });
      
      skipLink.addEventListener('blur', () => {
        skipLink.style.top = '-40px';
      });

      document.body.insertBefore(skipLink, document.body.firstChild);
    }
  }

  /**
   * Initialize all header functionality
   */
  function init() {
    initScrollEffect();
    initNavState();
    initSearch();
    initAccessibility();
  }

  // Public API
  return {
    init: init,
    performSearch: performSearch,
    clearSearchHighlight: clearSearchHighlight,
  };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', HeaderModule.init);
} else {
  HeaderModule.init();
}
