/**
 * ALETHEION INTERACTIONS MODULE
 * Handles card interactions, navigation, buttons, and hover effects
 */

const InteractionsModule = (() => {
    /**
     * Initialize card hover effects
     */
    function initCardHoverEffects() {
        const cards = document.querySelectorAll('[class*="card"], [class*="feature"]');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-12px)';
                this.style.transition = 'all 0.3s cubic-bezier(0.6, 0, 0.2, 1)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    }

    /**
     * Initialize button interactions
     */
    function initButtonInteractions() {
        const buttons = document.querySelectorAll('button, .btn');
        
        buttons.forEach(button => {
            button.addEventListener('mouseenter', function() {
                this.classList.add('btn-hover');
            });

            button.addEventListener('mouseleave', function() {
                this.classList.remove('btn-hover');
            });

            button.addEventListener('click', function(e) {
                // Add ripple effect
                const ripple = document.createElement('span');
                ripple.classList.add('ripple');
                this.appendChild(ripple);

                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;

                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';

                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    /**
     * Initialize navigation active state
     */
    function initNavigation() {
        const navItems = document.querySelectorAll('.nav-item');
        const currentPage = window.location.pathname.split('/').pop() || 'alt_home.html';

        navItems.forEach(item => {
            if (item.getAttribute('href') === currentPage) {
                item.classList.add('active');
            }

            item.addEventListener('click', function() {
                navItems.forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }

    /**
     * Initialize search functionality
     */
    function initSearch() {
        const searchInput = document.querySelector('.global-search input');
        
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            const query = e.target.value.toLowerCase();

            if (query.length < 2) return;

            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        });

        searchInput.addEventListener('focus', function() {
            this.parentElement.classList.add('search-active');
        });

        searchInput.addEventListener('blur', function() {
            this.parentElement.classList.remove('search-active');
        });
    }

    /**
     * Perform search functionality
     * @param {string} query - Search query
     */
    function performSearch(query) {
        console.log('Searching for:', query);
        
        // Highlight matching text in cards
        const cards = document.querySelectorAll('[class*="card"], h2, h3');
        
        cards.forEach(card => {
            const text = card.textContent.toLowerCase();
            if (text.includes(query)) {
                card.classList.add('search-highlight');
                card.style.opacity = '1';
            } else {
                card.classList.remove('search-highlight');
                card.style.opacity = '0.5';
            }
        });
    }

    /**
     * Clear search highlighting
     */
    function clearSearchHighlight() {
        document.querySelectorAll('.search-highlight').forEach(el => {
            el.classList.remove('search-highlight');
            el.style.opacity = '1';
        });
    }

    /**
     * Initialize dropdown menus
     */
    function initDropdowns() {
        const dropdowns = document.querySelectorAll('[data-dropdown]');
        
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('click', function(e) {
                e.stopPropagation();
                const menu = this.nextElementSibling;
                
                if (menu && menu.classList.contains('dropdown-menu')) {
                    menu.classList.toggle('show');
                    this.classList.toggle('active');
                }
            });
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', () => {
            document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
            document.querySelectorAll('[data-dropdown].active').forEach(btn => {
                btn.classList.remove('active');
            });
        });
    }

    /**
     * Initialize modal/dialog functionality
     * @param {string} triggerSelector - Selector for elements that trigger the modal
     * @param {string} modalSelector - Selector for the modal element
     */
    function initModal(triggerSelector, modalSelector) {
        const triggers = document.querySelectorAll(triggerSelector);
        const modal = document.querySelector(modalSelector);

        if (!modal) return;

        triggers.forEach(trigger => {
            trigger.addEventListener('click', () => {
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            });
        });

        const closeBtn = modal.querySelector('[data-close]') || modal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.remove('show');
                document.body.style.overflow = 'auto';
            });
        }

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
                document.body.style.overflow = 'auto';
            }
        });
    }

    /**
     * Initialize form interactions
     */
    function initFormInteractions() {
        const inputs = document.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            // Focus state
            input.addEventListener('focus', function() {
                this.parentElement?.classList.add('form-focus');
                this.classList.add('focused');
            });

            // Blur state
            input.addEventListener('blur', function() {
                this.parentElement?.classList.remove('form-focus');
                this.classList.remove('focused');
    
                // Keep focus state if input has value
                if (this.value) {
                    this.parentElement?.classList.add('form-focus');
                    this.classList.add('focused');
                }
            });

            // Filled state
            input.addEventListener('input', function() {
                if (this.value) {
                    this.parentElement?.classList.add('form-filled');
                } else {
                    this.parentElement?.classList.remove('form-filled');
                }
            });
        });
    }

    /**
     * Initialize tooltip functionality
     */
    function initTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        
        tooltips.forEach(element => {
            element.addEventListener('mouseenter', function() {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip-popup';
                tooltip.textContent = this.getAttribute('data-tooltip');
                document.body.appendChild(tooltip);

                const rect = this.getBoundingClientRect();
                tooltip.style.position = 'fixed';
                tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
                tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
                tooltip.style.opacity = '1';

                this.dataset.tooltip_ref = tooltip;
            });

            element.addEventListener('mouseleave', function() {
                const tooltip = this.dataset.tooltip_ref;
                if (tooltip && document.body.contains(tooltip)) {
                    tooltip.style.opacity = '0';
                    setTimeout(() => tooltip.remove(), 300);
                }
            });
        });
    }

    /**
     * Initialize lazy loading for images
     */
    function initLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.getAttribute('data-src');
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            });
        }, { threshold: 0.1 });

        images.forEach(img => imageObserver.observe(img));
    }

    /**
     * Initialize click tracking for analytics
     */
    function initClickTracking() {
        document.addEventListener('click', (e) => {
            const element = e.target;
            const trackingId = element.getAttribute('data-track');
            
            if (trackingId) {
                console.log('Click tracked:', trackingId);
                // Send to analytics service
                if (window.analytics) {
                    window.analytics.track('Element Clicked', {
                        elementId: trackingId,
                        timestamp: new Date().toISOString()
                    });
                }
            }
        });
    }

    /**
     * Initialize all interactions
     */
    function init() {
        initCardHoverEffects();
        initButtonInteractions();
        initNavigation();
        initSearch();
        initDropdowns();
        initFormInteractions();
        initTooltips();
        initLazyLoading();
        initClickTracking();
    }

    // Public API
    return {
        init: init,
        performSearch: performSearch,
        clearSearchHighlight: clearSearchHighlight,
        initModal: initModal,
        initCardHoverEffects: initCardHoverEffects,
        initButtonInteractions: initButtonInteractions
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', InteractionsModule.init);
} else {
    InteractionsModule.init();
}
