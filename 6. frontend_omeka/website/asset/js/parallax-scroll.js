/**
 * Parallax Scroll Module
 * Handles parallax tile movement based on scroll position
 * Simplified to avoid animation conflicts
 */

class ParallaxScroller {
  constructor() {
    this.tileLeftElements = [];
    this.tileRightElements = [];
    this.maxScrollOffset = 150; // Maximum parallax translation in pixels
    this.isInitialized = false;
    
    this.init();
  }

  init() {
    // Get all parallax tiles
    this.tileLeftElements = document.querySelectorAll('[data-parallax="left"]');
    this.tileRightElements = document.querySelectorAll('[data-parallax="right"]');

    if (this.tileLeftElements.length === 0 && this.tileRightElements.length === 0) {
      console.log('ParallaxScroller: No parallax tiles found, skipping init');
      return;
    }

    // Setup scroll event listener with RAF throttling
    this.setupScrollListener();
    
    // Initial update
    this.updateParallaxOffset();

    this.isInitialized = true;
    console.log('ParallaxScroller initialized with', this.tileLeftElements.length, 'left tiles and', this.tileRightElements.length, 'right tiles');
  }

  setupScrollListener() {
    let rafId = null;
    
    window.addEventListener('scroll', () => {
      if (rafId) {
        cancelAnimationFrame(rafId);
      }
      
      rafId = requestAnimationFrame(() => {
        this.updateParallaxOffset();
      });
    }, { passive: true });
  }

  updateParallaxOffset() {
    const parallaxSection = document.querySelector('.parallax-section');
    
    if (!parallaxSection) return;

    const rect = parallaxSection.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    
    // Calculate progress: 0 when section is below viewport, 1 when above
    // Centered around 0.5 when section is in middle of viewport
    let progress = (windowHeight - rect.top) / (windowHeight + rect.height);
    progress = Math.max(0, Math.min(1, progress)); // Clamp between 0 and 1
    
    // Center the progress so 0 offset is at 0.5 progress
    const centeredProgress = (progress - 0.5) * 2; // Range: -1 to 1

    // Apply parallax offset to left tiles (move left as scroll progresses)
    this.tileLeftElements.forEach((tile) => {
      const offset = centeredProgress * this.maxScrollOffset;
      tile.style.transform = `translateX(${-offset}px)`;
    });

    // Apply parallax offset to right tiles (move right as scroll progresses)
    this.tileRightElements.forEach((tile) => {
      const offset = centeredProgress * this.maxScrollOffset;
      tile.style.transform = `translateX(${offset}px)`;
    });
  }

  // Public method to update max scroll offset (responsive adjustment)
  setMaxOffset(value) {
    this.maxScrollOffset = value;
  }

  // Public method to destroy and cleanup
  destroy() {
    this.tileLeftElements = [];
    this.tileRightElements = [];
    this.isInitialized = false;
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.parallaxScroller = new ParallaxScroller();
});

// Reinitialize on window resize for responsive adjustments
window.addEventListener('resize', () => {
  if (window.parallaxScroller && window.parallaxScroller.isInitialized) {
    // Adjust max offset based on viewport width
    if (window.innerWidth < 768) {
      window.parallaxScroller.setMaxOffset(80);
    } else if (window.innerWidth < 1024) {
      window.parallaxScroller.setMaxOffset(120);
    } else {
      window.parallaxScroller.setMaxOffset(150);
    }
  }
});
