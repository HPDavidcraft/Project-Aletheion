/**
 * ALETHEION SLIDESHOW MODULE
 * Handles image carousels, slideshows, and gallery transitions
 */

const SlideshowModule = (() => {
    class Slideshow {
        constructor(containerId, options = {}) {
            this.container = document.getElementById(containerId);
            if (!this.container) {
                console.warn(`Slideshow container #${containerId} not found`);
                return;
            }

            // Options with defaults
            this.options = {
                auto: options.auto !== false,
                autoDelay: options.autoDelay || 5000,
                transition: options.transition || 'fade',
                transitionDuration: options.transitionDuration || 1.5,
                showArrows: options.showArrows !== false,
                showDots: options.showDots !== false,
                keyboard: options.keyboard !== false,
                ...options
            };

            // State
            this.slides = this.container.querySelectorAll('[data-slide]');
            this.currentIndex = 0;
            this.autoPlayTimer = null;

            if (this.slides.length === 0) {
                console.warn('No slides found in slideshow container');
                return;
            }

            this.init();
        }

        /**
         * Initialize slideshow
         */
        init() {
            this.setupSlides();
            if (this.options.showArrows) this.createArrows();
            if (this.options.showDots) this.createDots();
            if (this.options.keyboard) this.setupKeyboard();
            this.show(0);
            
            if (this.options.auto) {
                this.startAutoPlay();
            }

            // Pause on hover
            this.container.addEventListener('mouseenter', () => this.pauseAutoPlay());
            this.container.addEventListener('mouseleave', () => {
                if (this.options.auto) this.startAutoPlay();
            });
        }

        /**
         * Setup initial slide styles
         */
        setupSlides() {
            this.slides.forEach((slide, index) => {
                slide.style.position = 'absolute';
                slide.style.top = '0';
                slide.style.left = '0';
                slide.style.width = '100%';
                slide.style.height = '100%';
                slide.style.opacity = index === 0 ? '1' : '0';
                slide.style.transition = `opacity ${this.options.transitionDuration}s cubic-bezier(0.6, 0, 0.2, 1)`;
                slide.style.pointerEvents = index === 0 ? 'auto' : 'none';
            });
        }

        /**
         * Create navigation arrows
         */
        createArrows() {
            const prevBtn = document.createElement('button');
            prevBtn.className = 'slideshow-arrow prev';
            prevBtn.innerHTML = '&#10094;';
            prevBtn.addEventListener('click', () => this.prev());

            const nextBtn = document.createElement('button');
            nextBtn.className = 'slideshow-arrow next';
            nextBtn.innerHTML = '&#10095;';
            nextBtn.addEventListener('click', () => this.next());

            this.container.appendChild(prevBtn);
            this.container.appendChild(nextBtn);
        }

        /**
         * Create navigation dots
         */
        createDots() {
            const dotsContainer = document.createElement('div');
            dotsContainer.className = 'slideshow-dots';

            this.slides.forEach((_, index) => {
                const dot = document.createElement('button');
                dot.className = 'dot' + (index === 0 ? ' active' : '');
                dot.setAttribute('data-index', index);
                dot.addEventListener('click', () => this.goToSlide(index));
                dotsContainer.appendChild(dot);
            });

            this.container.appendChild(dotsContainer);
            this.dotsContainer = dotsContainer;
        }

        /**
         * Setup keyboard navigation
         */
        setupKeyboard() {
            document.addEventListener('keydown', (e) => {
                if (!this.container.closest('body')) return; // Check if visible
                
                if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    this.prev();
                } else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.next();
                }
            });
        }

        /**
         * Show slide at index
         * @param {number} index - Slide index
         */
        show(index) {
            if (index < 0) index = this.slides.length - 1;
            if (index >= this.slides.length) index = 0;

            // Update slides
            this.slides.forEach((slide, i) => {
                slide.style.opacity = i === index ? '1' : '0';
                slide.style.pointerEvents = i === index ? 'auto' : 'none';
            });

            // Update dots
            if (this.dotsContainer) {
                this.dotsContainer.querySelectorAll('.dot').forEach((dot, i) => {
                    if (i === index) {
                        dot.classList.add('active');
                    } else {
                        dot.classList.remove('active');
                    }
                });
            }

            this.currentIndex = index;
        }

        /**
         * Go to specific slide
         * @param {number} index - Slide index
         */
        goToSlide(index) {
            this.pauseAutoPlay();
            this.show(index);
            if (this.options.auto) this.startAutoPlay();
        }

        /**
         * Next slide
         */
        next() {
            this.pauseAutoPlay();
            this.show(this.currentIndex + 1);
            if (this.options.auto) this.startAutoPlay();
        }

        /**
         * Previous slide
         */
        prev() {
            this.pauseAutoPlay();
            this.show(this.currentIndex - 1);
            if (this.options.auto) this.startAutoPlay();
        }

        /**
         * Start auto play
         */
        startAutoPlay() {
            if (this.autoPlayTimer) clearInterval(this.autoPlayTimer);
            
            this.autoPlayTimer = setInterval(() => {
                this.show(this.currentIndex + 1);
            }, this.options.autoDelay);
        }

        /**
         * Pause auto play
         */
        pauseAutoPlay() {
            if (this.autoPlayTimer) {
                clearInterval(this.autoPlayTimer);
                this.autoPlayTimer = null;
            }
        }

        /**
         * Destroy slideshow
         */
        destroy() {
            this.pauseAutoPlay();
            this.container.querySelectorAll('.slideshow-arrow, .slideshow-dots').forEach(el => el.remove());
        }
    }

    /**
     * Initialize all slideshows on the page
     */
    function initAllSlideshows() {
        const slideshowContainers = document.querySelectorAll('[data-slideshow]');
        const slideshows = [];

        slideshowContainers.forEach(container => {
            const id = container.id || `slideshow-${Math.random().toString(36).substr(2, 9)}`;
            container.id = id;

            const options = {
                auto: container.getAttribute('data-auto') !== 'false',
                autoDelay: parseInt(container.getAttribute('data-delay')) || 5000,
                showArrows: container.getAttribute('data-arrows') !== 'false',
                showDots: container.getAttribute('data-dots') !== 'false'
            };

            const slideshow = new Slideshow(id, options);
            slideshows.push(slideshow);
        });

        return slideshows;
    }

    /**
     * Initialize a gallery with lightbox
     * @param {string} selector - Gallery container selector
     */
    function initGallery(selector) {
        const gallery = document.querySelector(selector);
        if (!gallery) return;

        const images = gallery.querySelectorAll('img');
        let currentImageIndex = 0;

        // Create lightbox
        const lightbox = document.createElement('div');
        lightbox.className = 'gallery-lightbox';
        lightbox.innerHTML = `
            <div class="lightbox-content">
                <button class="lightbox-close">&times;</button>
                <button class="lightbox-prev">&#10094;</button>
                <img class="lightbox-image" src="" alt="">
                <button class="lightbox-next">&#10095;</button>
                <div class="lightbox-counter">
                    <span class="current">1</span> / <span class="total">${images.length}</span>
                </div>
            </div>
        `;
        document.body.appendChild(lightbox);

        const lightboxImage = lightbox.querySelector('.lightbox-image');
        const closeBtn = lightbox.querySelector('.lightbox-close');
        const prevBtn = lightbox.querySelector('.lightbox-prev');
        const nextBtn = lightbox.querySelector('.lightbox-next');
        const counterCurrent = lightbox.querySelector('.current');

        const updateLightbox = (index) => {
            currentImageIndex = (index + images.length) % images.length;
            lightboxImage.src = images[currentImageIndex].src;
            lightboxImage.alt = images[currentImageIndex].alt;
            counterCurrent.textContent = currentImageIndex + 1;
        };

        // Image click to open lightbox
        images.forEach((img, index) => {
            img.addEventListener('click', () => {
                lightbox.classList.add('show');
                updateLightbox(index);
            });
            img.style.cursor = 'pointer';
        });

        // Lightbox controls
        closeBtn.addEventListener('click', () => lightbox.classList.remove('show'));
        prevBtn.addEventListener('click', () => updateLightbox(currentImageIndex - 1));
        nextBtn.addEventListener('click', () => updateLightbox(currentImageIndex + 1));

        // Close on background click
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) lightbox.classList.remove('show');
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!lightbox.classList.contains('show')) return;
            
            if (e.key === 'ArrowLeft') updateLightbox(currentImageIndex - 1);
            else if (e.key === 'ArrowRight') updateLightbox(currentImageIndex + 1);
            else if (e.key === 'Escape') lightbox.classList.remove('show');
        });
    }

    /**
     * Initialize carousel (alternative to slideshow)
     * @param {string} containerId - Container ID
     * @param {object} options - Configuration options
     */
    function initCarousel(containerId, options = {}) {
        const carousel = new Slideshow(containerId, {
            showArrows: true,
            showDots: true,
            ...options
        });
        return carousel;
    }

    /**
     * Initialize all slideshows and galleries
     */
    function init() {
        initAllSlideshows();
        
        // Initialize any galleries
        document.querySelectorAll('[data-gallery]').forEach(gallery => {
            const selector = '.' + gallery.className.split(' ')[0];
            initGallery(selector);
        });
    }

    // Public API
    return {
        init: init,
        Slideshow: Slideshow,
        initGallery: initGallery,
        initCarousel: initCarousel,
        initAllSlideshows: initAllSlideshows
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', SlideshowModule.init);
} else {
    SlideshowModule.init();
}
