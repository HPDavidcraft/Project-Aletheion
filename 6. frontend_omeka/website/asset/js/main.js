/**
 * ALETHEION - MAIN APPLICATION JS
 * Initializes all modules and provides global utilities
 */

// ============================================================================
// GLOBAL APPLICATION OBJECT
// ============================================================================

const Aletheion = (() => {
    // Configuration
    const config = {
        siteTitle: 'Project Aletheion',
        animationSpeed: 300,
        scrollOffset: 50,
        breakpoints: {
            mobile: 480,
            tablet: 768,
            desktop: 1024
        }
    };

    // State management
    const state = {
        isLoading: false,
        isMobile: window.innerWidth < config.breakpoints.tablet,
        currentPage: 'home',
        scrollPosition: 0
    };

    /**
     * Utility: Throttle function calls
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in ms
     */
    function throttle(func, limit = 300) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Utility: Debounce function calls
     * @param {Function} func - Function to debounce
     * @param {number} delay - Delay in ms
     */
    function debounce(func, delay = 300) {
        let timeoutId;
        return function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }

    /**
     * Utility: Check if element is in viewport
     * @param {HTMLElement} element - Element to check
     * @returns {boolean}
     */
    function isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }

    /**
     * Utility: Fetch data from API
     * @param {string} url - API endpoint
     * @param {object} options - Fetch options
     * @returns {Promise}
     */
    function fetchData(url, options = {}) {
        return fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .catch(error => {
            console.error('Fetch error:', error);
            throw error;
        });
    }

    /**
     * Utility: Store data in localStorage
     * @param {string} key - Storage key
     * @param {any} value - Value to store
     */
    function setStorage(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('localStorage not available:', e);
        }
    }

    /**
     * Utility: Retrieve data from localStorage
     * @param {string} key - Storage key
     * @returns {any}
     */
    function getStorage(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (e) {
            console.warn('localStorage not available:', e);
            return null;
        }
    }

    /**
     * Utility: Add CSS class
     * @param {HTMLElement} element - Target element
     * @param {string} className - Class name to add
     */
    function addClass(element, className) {
        if (element) element.classList.add(className);
    }

    /**
     * Utility: Remove CSS class
     * @param {HTMLElement} element - Target element
     * @param {string} className - Class name to remove
     */
    function removeClass(element, className) {
        if (element) element.classList.remove(className);
    }

    /**
     * Utility: Toggle CSS class
     * @param {HTMLElement} element - Target element
     * @param {string} className - Class name to toggle
     */
    function toggleClass(element, className) {
        if (element) element.classList.toggle(className);
    }

    /**
     * Utility: Has CSS class
     * @param {HTMLElement} element - Target element
     * @param {string} className - Class name to check
     */
    function hasClass(element, className) {
        return element?.classList.contains(className) || false;
    }

    /**
     * Utility: Set multiple styles
     * @param {HTMLElement} element - Target element
     * @param {object} styles - Styles object
     */
    function setStyles(element, styles) {
        if (!element) return;
        Object.assign(element.style, styles);
    }

    /**
     * Utility: Create element
     * @param {string} tag - HTML tag
     * @param {object} attributes - Attributes object
     * @param {string} text - Inner text
     * @returns {HTMLElement}
     */
    function createElement(tag, attributes = {}, text = '') {
        const element = document.createElement(tag);
        Object.assign(element, attributes);
        if (text) element.textContent = text;
        return element;
    }

    /**
     * Initialize responsive behavior
     */
    function initResponsive() {
        const handleResize = debounce(() => {
            state.isMobile = window.innerWidth < config.breakpoints.tablet;
            document.documentElement.setAttribute('data-mobile', state.isMobile);
        }, 300);

        window.addEventListener('resize', handleResize);
        
        // Set initial state
        document.documentElement.setAttribute('data-mobile', state.isMobile);
    }

    /**
     * Initialize scroll tracking
     */
    function initScrollTracking() {
        window.addEventListener('scroll', throttle(() => {
            state.scrollPosition = window.scrollY;
            
            // Add/remove scroll indicator classes
            if (window.scrollY > config.scrollOffset) {
                document.documentElement.classList.add('has-scrolled');
            } else {
                document.documentElement.classList.remove('has-scrolled');
            }
        }, 100), { passive: true });
    }

    /**
     * Initialize performance monitoring
     */
    function initPerformanceMonitoring() {
        if (!window.performance) return;

        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = window.performance.timing;
                const loadTime = perfData.loadEventEnd - perfData.navigationStart;
                
                console.log('Page load time:', loadTime, 'ms');

                // Send to analytics if available
                if (window.analytics) {
                    window.analytics.track('Page Loaded', {
                        loadTime: loadTime
                    });
                }
            }, 0);
        });
    }

    /**
     * Initialize keyboard shortcuts
     */
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('.global-search input');
                if (searchInput) searchInput.focus();
            }
        });
    }

    function initDeepMapToggle() {
        const toggle = document.querySelector('[data-deep-map-toggle]');
        const overlay = document.getElementById('deep-map-overlay');
        const close = overlay?.querySelector('[data-deep-map-close]');
        if (!toggle || !overlay || !close) return;

        const setOpen = (open) => {
            overlay.hidden = !open;
            toggle.setAttribute('aria-expanded', String(open));
            if (open) {
                overlay.focus();
            } else {
                toggle.focus();
            }
        };

        toggle.addEventListener('click', (event) => {
            event.preventDefault();
            setOpen(overlay.hidden);
        });
        close.addEventListener('click', () => setOpen(false));
        overlay.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') setOpen(false);
        });
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in ms
     */
    function notify(message, type = 'info', duration = 3000) {
        const notification = createElement('div', {
            className: `notification notification-${type}`
        }, message);

        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 10000;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }

    /**
     * Show loading spinner
     */
    function showLoader() {
        state.isLoading = true;
        const loader = document.getElementById('page-loader');
        if (loader) loader.style.display = 'flex';
    }

    /**
     * Hide loading spinner
     */
    function hideLoader() {
        state.isLoading = false;
        const loader = document.getElementById('page-loader');
        if (loader) loader.style.display = 'none';
    }

    /**
     * Initialize all modules and features
     */
    function init() {
        console.log('🏛️ Initializing Project Aletheion...');

        // Initialize modules
        if (window.AnimationsModule) {
            AnimationsModule.init();
            console.log('✓ Animations module initialized');
        }

        if (window.InteractionsModule) {
            InteractionsModule.init();
            console.log('✓ Interactions module initialized');
        }

        if (window.SlideshowModule) {
            SlideshowModule.init();
            console.log('✓ Slideshow module initialized');
        }

        // Initialize utilities
        initResponsive();
        initScrollTracking();
        initPerformanceMonitoring();
        initKeyboardShortcuts();
        initDeepMapToggle();

        console.log('✓ Application ready');
    }

    // Public API
    return {
        init: init,
        config: config,
        state: state,
        throttle: throttle,
        debounce: debounce,
        isInViewport: isInViewport,
        fetchData: fetchData,
        setStorage: setStorage,
        getStorage: getStorage,
        addClass: addClass,
        removeClass: removeClass,
        toggleClass: toggleClass,
        hasClass: hasClass,
        setStyles: setStyles,
        createElement: createElement,
        notify: notify,
        showLoader: showLoader,
        hideLoader: hideLoader
    };
})();

// ============================================================================
// AUTO-INITIALIZATION
// ============================================================================

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Aletheion.init);
} else {
    Aletheion.init();
}

// Make Aletheion globally accessible
window.Aletheion = Aletheion;

