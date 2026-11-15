/**
 * ALETHEION UTILITIES MODULE
 * Helper functions and utility methods
 */

const UtilitiesModule = (() => {
    /**
     * Format number with commas
     * @param {number} num - Number to format
     * @returns {string}
     */
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    /**
     * Parse URL parameters
     * @returns {object}
     */
    function getUrlParams() {
        const params = {};
        const queryString = window.location.search.slice(1);
        const pairs = queryString.split('&');

        pairs.forEach(pair => {
            const [key, value] = pair.split('=');
            if (key) {
                params[decodeURIComponent(key)] = value ? decodeURIComponent(value) : '';
            }
        });

        return params;
    }

    /**
     * Generate unique ID
     * @returns {string}
     */
    function generateId() {
        return `id-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Deep clone object
     * @param {object} obj - Object to clone
     * @returns {object}
     */
    function deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }

    /**
     * Check if object is empty
     * @param {object} obj - Object to check
     * @returns {boolean}
     */
    function isEmpty(obj) {
        return Object.keys(obj).length === 0;
    }

    /**
     * Merge objects
     * @param {...object} sources - Source objects
     * @returns {object}
     */
    function merge(...sources) {
        const result = {};
        sources.forEach(source => {
            Object.assign(result, source);
        });
        return result;
    }

    /**
     * Format date
     * @param {Date} date - Date object
     * @param {string} format - Format string (e.g., 'YYYY-MM-DD')
     * @returns {string}
     */
    function formatDate(date, format = 'YYYY-MM-DD') {
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    /**
     * Calculate time elapsed
     * @param {Date} date - Past date
     * @returns {string}
     */
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        let interval = seconds / 31536000;

        if (interval > 1) return Math.floor(interval) + ' years ago';
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + ' months ago';
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + ' days ago';
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + ' hours ago';
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + ' minutes ago';
        return Math.floor(seconds) + ' seconds ago';
    }

    /**
     * Validate email
     * @param {string} email - Email to validate
     * @returns {boolean}
     */
    function isValidEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }

    /**
     * Validate URL
     * @param {string} url - URL to validate
     * @returns {boolean}
     */
    function isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Sanitize HTML
     * @param {string} html - HTML string
     * @returns {string}
     */
    function sanitizeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }

    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @returns {Promise}
     */
    function copyToClipboard(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            return Promise.resolve();
        }
    }

    /**
     * Get query parameter
     * @param {string} param - Parameter name
     * @returns {string|null}
     */
    function getQueryParam(param) {
        const params = getUrlParams();
        return params[param] || null;
    }

    /**
     * Detect device type
     * @returns {string}
     */
    function detectDevice() {
        const ua = navigator.userAgent;
        if (/mobile/i.test(ua)) return 'mobile';
        if (/tablet/i.test(ua)) return 'tablet';
        return 'desktop';
    }

    /**
     * Check if touch device
     * @returns {boolean}
     */
    function isTouchDevice() {
        return (('ontouchstart' in window) ||
                (navigator.maxTouchPoints > 0) ||
                (navigator.msMaxTouchPoints > 0));
    }

    /**
     * Get current theme
     * @returns {string}
     */
    function getCurrentTheme() {
        if (typeof localStorage !== 'undefined') {
            return localStorage.getItem('theme') || 'light';
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    /**
     * Set theme
     * @param {string} theme - 'light' or 'dark'
     */
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('theme', theme);
        }
    }

    /**
     * Load script dynamically
     * @param {string} src - Script source
     * @param {object} attributes - Additional attributes
     * @returns {Promise}
     */
    function loadScript(src, attributes = {}) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            Object.assign(script, attributes);

            script.onload = () => resolve(script);
            script.onerror = () => reject(new Error(`Failed to load script: ${src}`));

            document.head.appendChild(script);
        });
    }

    /**
     * Load stylesheet dynamically
     * @param {string} href - Stylesheet href
     * @returns {Promise}
     */
    function loadStylesheet(href) {
        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;

            link.onload = () => resolve(link);
            link.onerror = () => reject(new Error(`Failed to load stylesheet: ${href}`));

            document.head.appendChild(link);
        });
    }

    /**
     * Debounced resize event
     * @param {Function} callback - Callback function
     * @param {number} delay - Delay in ms
     * @returns {void}
     */
    function onWindowResize(callback, delay = 300) {
        let timeoutId;
        window.addEventListener('resize', () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(callback, delay);
        });
    }

    /**
     * Get scroll position
     * @returns {object}
     */
    function getScrollPosition() {
        return {
            x: window.scrollX || window.pageXOffset,
            y: window.scrollY || window.pageYOffset
        };
    }

    /**
     * Scroll to element
     * @param {HTMLElement|string} target - Element or selector
     * @param {object} options - Scroll options
     */
    function scrollToElement(target, options = {}) {
        let element = target;
        if (typeof target === 'string') {
            element = document.querySelector(target);
        }

        if (!element) return;

        const behavior = options.behavior || 'smooth';
        const block = options.block || 'start';
        const inline = options.inline || 'nearest';

        element.scrollIntoView({ behavior, block, inline });
    }

    /**
     * Check browser support
     * @param {string} feature - Feature name
     * @returns {boolean}
     */
    function isFeatureSupported(feature) {
        const features = {
            localStorage: typeof Storage !== 'undefined',
            sessionStorage: typeof sessionStorage !== 'undefined',
            indexedDB: typeof indexedDB !== 'undefined',
            serviceWorker: 'serviceWorker' in navigator,
            webGL: (() => {
                try {
                    const canvas = document.createElement('canvas');
                    return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
                } catch {
                    return false;
                }
            })(),
            fetch: typeof fetch !== 'undefined',
            promises: typeof Promise !== 'undefined'
        };

        return features[feature] || false;
    }

    /**
     * Batch API calls with rate limiting
     * @param {Array} requests - Array of URLs
     * @param {number} batchSize - Number of concurrent requests
     * @returns {Promise}
     */
    function batchFetch(requests, batchSize = 3) {
        const results = [];
        let completed = 0;

        return new Promise((resolve, reject) => {
            const processBatch = (startIndex) => {
                const batch = requests.slice(startIndex, startIndex + batchSize);
                if (batch.length === 0) {
                    if (completed === requests.length) {
                        resolve(results);
                    }
                    return;
                }

                Promise.all(batch.map(req => fetch(req)))
                    .then(responses => {
                        results.push(...responses);
                        completed += batch.length;
                        processBatch(startIndex + batchSize);
                    })
                    .catch(reject);
            };

            processBatch(0);
        });
    }

    // Public API
    return {
        formatNumber: formatNumber,
        getUrlParams: getUrlParams,
        generateId: generateId,
        deepClone: deepClone,
        isEmpty: isEmpty,
        merge: merge,
        formatDate: formatDate,
        timeAgo: timeAgo,
        isValidEmail: isValidEmail,
        isValidUrl: isValidUrl,
        sanitizeHtml: sanitizeHtml,
        copyToClipboard: copyToClipboard,
        getQueryParam: getQueryParam,
        detectDevice: detectDevice,
        isTouchDevice: isTouchDevice,
        getCurrentTheme: getCurrentTheme,
        setTheme: setTheme,
        loadScript: loadScript,
        loadStylesheet: loadStylesheet,
        onWindowResize: onWindowResize,
        getScrollPosition: getScrollPosition,
        scrollToElement: scrollToElement,
        isFeatureSupported: isFeatureSupported,
        batchFetch: batchFetch
    };
})();

// Make utilities globally accessible
window.Utils = UtilitiesModule;
