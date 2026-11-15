/**
 * ANIMATION OBSERVER MODULE
 * Handles scroll-triggered animations using Intersection Observer
 */

const AnimationObserver = (() => {
  const config = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px',
  };

  let observer = null;

  /**
   * Initialize Intersection Observer for scroll animations
   */
  function initObserver() {
    observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Trigger animation
          entry.target.classList.add('in-view');
          
          // Optionally unobserve after animation
          if (entry.target.hasAttribute('data-observe-once')) {
            observer.unobserve(entry.target);
          }
        }
      });
    }, config);

    // Observe all elements with animation classes
    document.querySelectorAll('[class*="animate-"], [data-section]').forEach(el => {
      observer.observe(el);
    });
  }

  /**
   * Observe element for animation
   */
  function observe(element) {
    if (observer) {
      observer.observe(element);
    }
  }

  /**
   * Unobserve element
   */
  function unobserve(element) {
    if (observer) {
      observer.unobserve(element);
    }
  }

  /**
   * Add stagger delay to children
   */
  function addStaggerDelay(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    container.querySelectorAll('> *').forEach((child, index) => {
      child.style.animationDelay = `${index * 0.1}s`;
    });
  }

  /**
   * Reveal elements on scroll with fade-in
   */
  function revealOnScroll(selector) {
    const elements = document.querySelectorAll(selector);
    elements.forEach(el => {
      el.classList.add('animate-fade-in-up');
      observer.observe(el);
    });
  }

  /**
   * Initialize counter animations
   */
  function initCounterAnimations() {
    const counters = document.querySelectorAll('.stat-number');
    counters.forEach(counter => {
      const target = parseInt(counter.getAttribute('data-count'));
      
      // Observe counter to start animation when visible
      const tempObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            animateCounter(counter, target);
            tempObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.5 });

      tempObserver.observe(counter);
    });
  }

  /**
   * Animate counter from 0 to target
   */
  function animateCounter(element, target) {
    let current = 0;
    const increment = target / 50;
    const duration = 2000; // 2 seconds
    const step = duration / 50;

    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        element.textContent = target.toLocaleString() + '+';
        clearInterval(timer);
      } else {
        element.textContent = Math.floor(current).toLocaleString() + '+';
      }
    }, step);
  }

  /**
   * Initialize parallax effect for background images
   */
  function initParallax(selector) {
    const elements = document.querySelectorAll(selector);
    
    window.addEventListener('scroll', () => {
      elements.forEach(el => {
        const rect = el.getBoundingClientRect();
        const scrollPercentage = (window.innerHeight - rect.top) / (window.innerHeight + rect.height);
        
        if (scrollPercentage > 0 && scrollPercentage < 1) {
          el.style.backgroundPosition = `center ${scrollPercentage * 50}px`;
        }
      });
    }, { passive: true });
  }

  /**
   * Initialize floating animation for elements
   */
  function initFloatingIcons(selector) {
    const elements = document.querySelectorAll(selector);
    
    elements.forEach((el, index) => {
      const delay = index * 0.2;
      el.style.animation = `float 3s ease-in-out ${delay}s infinite`;
    });
  }

  /**
   * Initialize all animations
   */
  function init() {
    initObserver();
    initCounterAnimations();
    revealOnScroll('[data-section]');
  }

  // Public API
  return {
    init: init,
    observe: observe,
    unobserve: unobserve,
    addStaggerDelay: addStaggerDelay,
    revealOnScroll: revealOnScroll,
    initParallax: initParallax,
    initFloatingIcons: initFloatingIcons,
    initCounterAnimations: initCounterAnimations,
  };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', AnimationObserver.init);
} else {
  AnimationObserver.init();
}
