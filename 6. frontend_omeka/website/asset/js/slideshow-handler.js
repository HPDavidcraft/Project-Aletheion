/**
 * SLIDESHOW HANDLER MODULE
 * Manages slide transitions, auto-advance, and keyboard controls
 */

const SlideshowHandler = (() => {
  const config = {
    currentSlide: 0,
    totalSlides: 0,
    autoPlayInterval: 8000, // 8 seconds
    transitionDuration: 800, // 800ms
    isAutoPlaying: true,
    autoPlayTimer: null,
  };

  /**
   * Get total number of slides from DOM
   */
  function getTotalSlides() {
    const slides = document.querySelectorAll('.slide');
    return slides.length;
  }

  /**
   * Display slide at index
   */
  function displaySlide(index) {
    const slides = document.querySelectorAll('.slide');
    
    if (slides.length === 0) return;

    // Normalize index
    if (index >= slides.length) {
      config.currentSlide = 0;
    } else if (index < 0) {
      config.currentSlide = slides.length - 1;
    } else {
      config.currentSlide = index;
    }

    // Hide all slides
    slides.forEach(slide => {
      slide.classList.remove('active');
      slide.style.opacity = '0';
      slide.style.zIndex = '0';
    });

    // Show current slide
    const activeSlide = slides[config.currentSlide];
    activeSlide.classList.add('active');
    activeSlide.style.opacity = '1';
    activeSlide.style.zIndex = '10';

    // Update slide indicators if they exist
    updateIndicators();
  }

  /**
   * Update slide indicators (dots or numbers)
   */
  function updateIndicators() {
    const indicators = document.querySelectorAll('.slide-indicator');
    
    indicators.forEach((indicator, index) => {
      if (index === config.currentSlide) {
        indicator.classList.add('active');
      } else {
        indicator.classList.remove('active');
      }
    });
  }

  /**
   * Show next slide
   */
  function nextSlide() {
    displaySlide(config.currentSlide + 1);
    resetAutoPlay();
  }

  /**
   * Show previous slide
   */
  function prevSlide() {
    displaySlide(config.currentSlide - 1);
    resetAutoPlay();
  }

  /**
   * Start auto-play
   */
  function startAutoPlay() {
    if (!config.isAutoPlaying) return;

    config.autoPlayTimer = setInterval(() => {
      nextSlide();
    }, config.autoPlayInterval);
  }

  /**
   * Stop auto-play
   */
  function stopAutoPlay() {
    if (config.autoPlayTimer) {
      clearInterval(config.autoPlayTimer);
      config.autoPlayTimer = null;
    }
  }

  /**
   * Reset auto-play timer
   */
  function resetAutoPlay() {
    stopAutoPlay();
    if (config.isAutoPlaying) {
      startAutoPlay();
    }
  }

  /**
   * Initialize slideshow arrow buttons
   */
  function initArrowButtons() {
    const prevBtn = document.querySelector('.slideshow-prev');
    const nextBtn = document.querySelector('.slideshow-next');

    if (prevBtn) {
      prevBtn.addEventListener('click', prevSlide);
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', nextSlide);
    }
  }

  /**
   * Initialize keyboard controls
   */
  function initKeyboardControls() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') {
        prevSlide();
      } else if (e.key === 'ArrowRight') {
        nextSlide();
      }
    });
  }

  /**
   * Initialize pause on hover
   */
  function initPauseOnHover() {
    const slideshow = document.querySelector('.slideshow');
    
    if (slideshow) {
      slideshow.addEventListener('mouseenter', stopAutoPlay);
      slideshow.addEventListener('mouseleave', startAutoPlay);
    }
  }

  /**
   * Initialize slide indicators (dots)
   */
  function initIndicators() {
    const dots = document.querySelectorAll('.slide-indicator');
    
    dots.forEach((dot, index) => {
      dot.addEventListener('click', () => {
        displaySlide(index);
        resetAutoPlay();
      });
    });
  }

  /**
   * Jump to specific slide
   */
  function goToSlide(index) {
    displaySlide(index);
    resetAutoPlay();
  }

  /**
   * Set auto-play duration
   */
  function setAutoPlayDuration(ms) {
    config.autoPlayInterval = ms;
    resetAutoPlay();
  }

  /**
   * Enable/disable auto-play
   */
  function setAutoPlay(enabled) {
    config.isAutoPlaying = enabled;
    if (enabled) {
      startAutoPlay();
    } else {
      stopAutoPlay();
    }
  }

  /**
   * Initialize slideshow
   */
  function init() {
    config.totalSlides = getTotalSlides();
    
    if (config.totalSlides === 0) return;

    // Initialize first slide
    displaySlide(0);

    // Initialize all controls
    initArrowButtons();
    initKeyboardControls();
    initPauseOnHover();
    initIndicators();

    // Start auto-play
    if (config.isAutoPlaying) {
      startAutoPlay();
    }
  }

  // Public API
  return {
    init: init,
    nextSlide: nextSlide,
    prevSlide: prevSlide,
    goToSlide: goToSlide,
    displaySlide: displaySlide,
    startAutoPlay: startAutoPlay,
    stopAutoPlay: stopAutoPlay,
    setAutoPlayDuration: setAutoPlayDuration,
    setAutoPlay: setAutoPlay,
    getCurrentSlide: () => config.currentSlide,
    getTotalSlides: () => config.totalSlides,
  };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', SlideshowHandler.init);
} else {
  SlideshowHandler.init();
}
