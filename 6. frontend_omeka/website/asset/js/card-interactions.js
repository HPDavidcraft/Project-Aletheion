/**
 * CARD INTERACTIONS MODULE
 * Handles click navigation and hover effects for card components
 */

const CardInteractions = (() => {
  /**
   * Initialize feature card navigation
   */
  function initFeatureCards() {
    const cards = document.querySelectorAll('.feature-card');
    
    cards.forEach(card => {
      // Add click handler for navigation
      card.addEventListener('click', (e) => {
        const url = card.getAttribute('data-url');
        if (url) {
          window.location.href = url;
        }
      });

      // Add hover lift effect
      card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-8px)';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0)';
      });

      // Add cursor pointer
      card.style.cursor = 'pointer';
    });
  }

  /**
   * Initialize site mini cards
   */
  function initMiniCards() {
    const miniCards = document.querySelectorAll('.site-mini-card');
    
    miniCards.forEach(card => {
      card.addEventListener('click', () => {
        const url = card.getAttribute('data-url') || card.getAttribute('href');
        if (url) {
          window.location.href = url;
        }
      });

      card.style.cursor = 'pointer';
    });
  }

  /**
   * Initialize pill/button interactions
   */
  function initPills() {
    const pills = document.querySelectorAll('.pill');
    
    pills.forEach(pill => {
      pill.addEventListener('click', (e) => {
        const href = pill.getAttribute('href') || pill.getAttribute('data-href');
        if (href) {
          e.preventDefault();
          window.location.href = href;
        }
      });
    });
  }

  /**
   * Initialize discovery list items
   */
  function initDiscoveryItems() {
    const items = document.querySelectorAll('.discovery-item');
    
    items.forEach(item => {
      item.addEventListener('click', () => {
        const url = item.getAttribute('data-url') || item.querySelector('a')?.href;
        if (url) {
          window.location.href = url;
        }
      });

      item.addEventListener('mouseenter', () => {
        item.classList.add('expanded');
      });

      item.addEventListener('mouseleave', () => {
        item.classList.remove('expanded');
      });

      item.style.cursor = 'pointer';
    });
  }

  /**
   * Initialize science module cards
   */
  function initScienceModules() {
    const modules = document.querySelectorAll('.sci-module');
    
    modules.forEach(module => {
      const link = module.querySelector('a');
      if (link) {
        module.addEventListener('click', (e) => {
          if (e.target !== link) {
            link.click();
          }
        });

        module.style.cursor = 'pointer';
      }
    });
  }

  /**
   * Initialize key feature items
   */
  function initKeyFeatures() {
    const items = document.querySelectorAll('.key-feature-item');
    
    items.forEach(item => {
      const link = item.querySelector('a');
      if (link) {
        item.addEventListener('click', (e) => {
          if (e.target !== link && !e.target.closest('a')) {
            link.click();
          }
        });

        item.style.cursor = 'pointer';
      }
    });
  }

  /**
   * Add ripple effect on click
   */
  function addRippleEffect(element, event) {
    const rect = element.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.left = x + 'px';
    ripple.style.top = y + 'px';
    
    element.appendChild(ripple);

    setTimeout(() => {
      ripple.remove();
    }, 600);
  }

  /**
   * Initialize ripple effects on cards
   */
  function initRippleEffects() {
    const rippleElements = document.querySelectorAll('.feature-card, .pill, .science-btn');
    
    rippleElements.forEach(element => {
      element.addEventListener('click', (event) => {
        addRippleEffect(element, event);
      });
    });
  }

  /**
   * Initialize all card interactions
   */
  function init() {
    initFeatureCards();
    initMiniCards();
    initPills();
    initDiscoveryItems();
    initScienceModules();
    initKeyFeatures();
    initRippleEffects();
  }

  // Public API
  return {
    init: init,
    initFeatureCards: initFeatureCards,
    initMiniCards: initMiniCards,
    initPills: initPills,
    initDiscoveryItems: initDiscoveryItems,
    initScienceModules: initScienceModules,
    initKeyFeatures: initKeyFeatures,
    addRippleEffect: addRippleEffect,
  };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', CardInteractions.init);
} else {
  CardInteractions.init();
}
