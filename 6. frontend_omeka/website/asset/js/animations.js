/**
 * ALETHEION ANIMATIONS MODULE
 * Handles scroll-triggered animations, fade-ins, and interactive effects
 */

const AnimationsModule = (() => {
    // Private variables
    const animationConfig = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const animationClasses = {
        fadeInDown: 'animate-fade-in-down',
        fadeInUp: 'animate-fade-in-up',
        slideUp: 'animate-slide-up',
        scaleIn: 'animate-scale-in'
    };

    /**
     * Initialize Intersection Observer for scroll animations
     */
    function initScrollObserver() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    observer.unobserve(entry.target);
                }
            });
        }, animationConfig);

        // Observe all animated elements
        document.querySelectorAll('[class*="animate-"]').forEach(el => {
            observer.observe(el);
        });

        return observer;
    }

    /**
     * Add scroll effect to header
     */
    function initHeaderScrollEffect() {
        window.addEventListener('scroll', () => {
            const header = document.querySelector('header');
            if (!header) return;

            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    /**
     * Animate counter numbers on load
     * @param {HTMLElement} element - The counter element
     * @param {number} target - Target number to count to
     */
    function animateCounter(element, target) {
        element.classList.add('animate-fade-in-up');

        let current = 0;
        const increment = target / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target.toLocaleString() + '+';
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current).toLocaleString() + '+';
            }
        }, 20);
    }

    /**
     * Initialize all counter animations
     */
    function initCounterAnimations() {
        const counters = document.querySelectorAll('.stat-number');
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-count'));
            if (!isNaN(target)) {
                animateCounter(counter, target);
            }
        });
    }

    /**
     * Add stagger delay to elements
     * @param {string} selector - CSS selector for elements
     */
    function addStaggerDelay(selector) {
        document.querySelectorAll(selector).forEach((el, index) => {
            el.style.animationDelay = `${index * 0.1}s`;
        });
    }

    /**
     * Fade in text character by character (typing effect)
     * @param {HTMLElement} element - Element containing text
     * @param {number} speed - Speed of typing in ms
     */
    function typewriterEffect(element, speed = 50) {
        const text = element.textContent;
        element.textContent = '';
        let index = 0;

        const type = () => {
            if (index < text.length) {
                element.textContent += text.charAt(index);
                index++;
                setTimeout(type, speed);
            }
        };

        type();
    }

    /**
     * Add pulse animation to elements
     * @param {string} selector - CSS selector for elements
     */
    function addPulseAnimation(selector) {
        document.querySelectorAll(selector).forEach(el => {
            el.classList.add('btn-pulse');
        });
    }

    /**
     * Reveal elements on scroll with fade-in
     * @param {string} selector - CSS selector for elements to reveal
     */
    function revealOnScroll(selector) {
        const elements = document.querySelectorAll(selector);
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        elements.forEach(el => revealObserver.observe(el));
    }

    /**
     * Initialize float animation for icons
     * @param {string} selector - CSS selector for icons
     */
    function initFloatingIcons(selector) {
        document.querySelectorAll(selector).forEach(el => {
            // Don't float header icons (nav-icon, icon-lang, icon-login)
            if (el.closest('header')) return;
            el.classList.add('icon-float');
        });
    }

    /**
     * Create a smooth scroll animation
     * @param {string} selector - Target element selector
     * @param {number} duration - Duration in ms
     */
    function smoothScroll(selector, duration = 1000) {
        const target = document.querySelector(selector);
        if (!target) return;

        const start = window.scrollY;
        const end = target.getBoundingClientRect().top + window.scrollY;
        const distance = end - start;
        let startTime = null;

        const easeInOutQuad = (t) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

        const animation = (currentTime) => {
            if (startTime === null) startTime = currentTime;
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const ease = easeInOutQuad(progress);

            window.scrollTo(0, start + distance * ease);

            if (progress < 1) {
                requestAnimationFrame(animation);
            }
        };

        requestAnimationFrame(animation);
    }

    /**
     * Add element to viewport check (useful for lazy loading)
     * @param {string} selector - CSS selector
     * @param {Function} callback - Callback when element enters viewport
     */
    function onViewport(selector, callback) {
        const elements = document.querySelectorAll(selector);
        const viewportObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    callback(entry.target);
                    viewportObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        elements.forEach(el => viewportObserver.observe(el));
    }

    /**
     * Initialize all animations
     */
    function init() {
        initScrollObserver();
        initHeaderScrollEffect();
        initCounterAnimations();
        addStaggerDelay('[class*="animate-"]');
        revealOnScroll('.stagger-item');
        initFloatingIcons('[class*="icon"]');

        // Apply stagger delays to grid items
        const gridItems = document.querySelectorAll('[class*="card"], [class*="item"]');
        gridItems.forEach((el, index) => {
            el.style.animationDelay = `${index * 0.08}s`;
        });
    }

    // Public API
    return {
        init: init,
        animateCounter: animateCounter,
        typewriterEffect: typewriterEffect,
        addPulseAnimation: addPulseAnimation,
        revealOnScroll: revealOnScroll,
        smoothScroll: smoothScroll,
        onViewport: onViewport,
        addStaggerDelay: addStaggerDelay,
        initFloatingIcons: initFloatingIcons
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', AnimationsModule.init);
} else {
    AnimationsModule.init();
}
