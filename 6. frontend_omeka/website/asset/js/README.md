# Aletheion JavaScript Modules Documentation

## Overview

The Aletheion project uses a modular JavaScript architecture with specialized modules for animations, interactions, slideshows, and utilities. All modules are self-contained and can be used independently or together.

---

## 📁 JavaScript Files

### 1. **main.js** - Core Application Module
Primary entry point that initializes all modules and provides global utilities.

**Key Features:**
- Global `Aletheion` object with configuration and state management
- Throttle and debounce utilities
- DOM utility functions (addClass, removeClass, toggleClass, etc.)
- Responsive behavior initialization
- Scroll tracking and performance monitoring
- Keyboard shortcuts support
- Notification system

**Usage:**
```javascript
// Access the Aletheion object
Aletheion.notify('Welcome!', 'success');
Aletheion.setStorage('key', value);
const value = Aletheion.getStorage('key');
Aletheion.addClass(element, 'className');
Aletheion.addClass(element, 'className');
```

**Available Methods:**
- `init()` - Initialize all modules
- `throttle(func, limit)` - Throttle function calls
- `debounce(func, delay)` - Debounce function calls
- `isInViewport(element)` - Check if element is visible
- `fetchData(url, options)` - Fetch data from API
- `setStorage(key, value)` - Store in localStorage
- `getStorage(key)` - Retrieve from localStorage
- `addClass/removeClass/toggleClass/hasClass` - DOM class utilities
- `setStyles(element, styles)` - Apply multiple styles
- `createElement(tag, attributes, text)` - Create DOM elements
- `notify(message, type, duration)` - Show notifications
- `showLoader()` / `hideLoader()` - Display loading spinner

---

### 2. **animations.js** - Animation & Scroll Effects
Handles all scroll-triggered animations and visual effects.

**Key Features:**
- Intersection Observer for viewport-triggered animations
- Scroll effects on header (add 'scrolled' class)
- Counter number animations
- Typewriter text effect
- Staggered animation delays
- Floating icon animations
- Smooth scroll functionality
- Fade-in on scroll reveals

**Usage:**
```javascript
// Already auto-initialized, but can be called manually:
AnimationsModule.init();

// Animate a counter
AnimationsModule.animateCounter(element, targetNumber);

// Add typewriter effect
AnimationsModule.typewriterEffect(element, speed);

// Reveal elements on scroll
AnimationsModule.revealOnScroll('.selector');

// Smooth scroll to element
AnimationsModule.smoothScroll('#target-id');

// Execute callback when element enters viewport
AnimationsModule.onViewport('.selector', (element) => {
    console.log('Element is now visible:', element);
});
```

**Animation Classes Used in HTML:**
- `.animate-fade-in-down` - Fade in from top
- `.animate-fade-in-up` - Fade in from bottom
- `.animate-slide-up` - Slide up animation
- `.animate-scale-in` - Scale in from center

---

### 3. **interactions.js** - User Interactions
Handles card interactions, button effects, navigation, and form inputs.

**Key Features:**
- Card hover lift effects (translateY)
- Button ripple effects
- Navigation active state management
- Search functionality with highlighting
- Dropdown menu management
- Modal/dialog functionality
- Form focus states and validation
- Tooltip system
- Lazy image loading
- Click tracking for analytics

**Usage:**
```javascript
// Already auto-initialized
InteractionsModule.init();

// Perform search
InteractionsModule.performSearch('query');

// Clear search highlighting
InteractionsModule.clearSearchHighlight();

// Initialize modal
InteractionsModule.initModal('.trigger-selector', '.modal-selector');

// Form interactions are auto-initialized:
// - Focus states
// - Filled states
// - Blur states
```

**Features:**
- Cards lift on hover (`transform: translateY(-12px)`)
- Form inputs show glow effect on focus
- Search highlights matching content
- Navigation items show active state
- Buttons create ripple effect on click

---

### 4. **slideshow.js** - Carousels & Galleries
Complete slideshow, carousel, and image gallery functionality.

**Key Features:**
- Automatic slideshow with configurable timing
- Manual navigation (arrows)
- Dot indicators
- Keyboard navigation (arrow keys)
- Pause on hover
- Image lightbox with zoom
- Gallery functionality
- Touch gesture support ready

**Usage:**
```javascript
// Auto-initialize all slideshows with data attributes
SlideshowModule.init();

// Manual slideshow creation
const gallery = new SlideshowModule.Slideshow('container-id', {
    auto: true,           // Auto-play
    autoDelay: 5000,      // 5 seconds between slides
    showArrows: true,     // Show navigation arrows
    showDots: true,       // Show dot indicators
    keyboard: true,       // Enable arrow key navigation
    transitionDuration: 1.5 // Transition time in seconds
});

// Slideshow methods
gallery.next();              // Next slide
gallery.prev();              // Previous slide
gallery.goToSlide(index);    // Jump to slide
gallery.startAutoPlay();     // Resume autoplay
gallery.pauseAutoPlay();     // Pause autoplay
gallery.destroy();           // Clean up

// Initialize gallery with lightbox
SlideshowModule.initGallery('.gallery-selector');
```

**HTML Setup for Slideshows:**
```html
<div id="my-slideshow" data-slideshow data-auto="true" data-delay="5000">
    <div data-slide><img src="slide1.jpg" alt="Slide 1"></div>
    <div data-slide><img src="slide2.jpg" alt="Slide 2"></div>
</div>
```

---

### 5. **utilities.js** - Helper Functions
Collection of utility functions for common tasks.

**Key Features:**
- Number and date formatting
- URL parameter parsing
- Object manipulation (clone, merge, isEmpty)
- Email and URL validation
- HTML sanitization
- Clipboard operations
- Device detection
- Theme management
- Dynamic script/stylesheet loading
- Scroll utilities
- Browser feature detection
- Batch API calls with rate limiting

**Usage:**
```javascript
// Access via window.Utils
Utils.formatNumber(1000000);           // "1,000,000"
Utils.getUrlParams();                  // { param: 'value' }
Utils.generateId();                    // "id-1234567890-abc123"
Utils.formatDate(new Date());          // "2024-02-13"
Utils.timeAgo(pastDate);               // "2 hours ago"

// Validation
Utils.isValidEmail('test@example.com');
Utils.isValidUrl('https://example.com');

// Form utilities
Utils.copyToClipboard('text');
Utils.sanitizeHtml('<script>alert("xss")</script>');

// Device detection
Utils.detectDevice();                  // "mobile", "tablet", or "desktop"
Utils.isTouchDevice();                 // true/false

// Theme management
Utils.setTheme('dark');
const theme = Utils.getCurrentTheme();

// Dynamic loading
Utils.loadScript('path/to/script.js');
Utils.loadStylesheet('path/to/style.css');

// Browser features
Utils.isFeatureSupported('localStorage');
Utils.isFeatureSupported('serviceWorker');

// Scroll utilities
Utils.scrollToElement('#target');
Utils.getScrollPosition();              // { x: 0, y: 100 }
```

---

## 🎯 Module Initialization Order

1. **HTML loads scripts** (in order):
   ```html
   <script src="asset/js/utilities.js"></script>
   <script src="asset/js/animations.js"></script>
   <script src="asset/js/interactions.js"></script>
   <script src="asset/js/slideshow.js"></script>
   <script src="asset/js/main.js"></script>
   ```

2. **DOMContentLoaded event** triggers auto-initialization:
   - Aletheion.init() initializes all modules
   - Each module initializes its features
   - Console logs show initialization status

---

## 🎨 Animation Classes Reference

Add these classes to HTML elements for automatic scroll-triggered animations:

```html
<!-- Fade in from top -->
<div class="animate-fade-in-down">Content</div>

<!-- Fade in from bottom -->
<div class="animate-fade-in-up">Content</div>

<!-- Slide up from bottom -->
<div class="animate-slide-up">Content</div>

<!-- Scale in from center -->
<div class="animate-scale-in">Content</div>

<!-- Wrapper for staggered child animations -->
<div class="animate-container">
    <div class="animate-fade-in-down">Item 1</div>
    <div class="animate-fade-in-down">Item 2</div>
    <div class="animate-fade-in-down">Item 3</div>
</div>
```

---

## 📊 Data Attributes Reference

Use these HTML data attributes to configure features:

```html
<!-- Slideshow configuration -->
<div data-slideshow 
     data-auto="true" 
     data-delay="5000" 
     data-arrows="true" 
     data-dots="true">
    <!-- Slides -->
</div>

<!-- Tooltip -->
<button data-tooltip="Help text">Hover me</button>

<!-- Dropdown trigger -->
<button data-dropdown>Menu</button>
<div class="dropdown-menu">Options</div>

<!-- Click tracking -->
<button data-track="button-clicked">Click</button>

<!-- Gallery/Lightbox -->
<div data-gallery>
    <img data-src="image.jpg" alt="Image">
</div>
```

---

## 🔧 Configuration

Edit `main.js` to customize:

```javascript
const config = {
    siteTitle: 'Project Aletheion',
    animationSpeed: 300,           // Global animation duration (ms)
    scrollOffset: 50,              // Scroll threshold for effects
    breakpoints: {
        mobile: 480,
        tablet: 768,
        desktop: 1024
    }
};
```

---

## 🐛 Debugging

Enable verbose logging:

```javascript
// Log animations
console.log('Animated elements:', document.querySelectorAll('[class*="animate-"]'));

// Check module status
console.log('Aletheion:', Aletheion);
console.log('Animations:', AnimationsModule);
console.log('Interactions:', InteractionsModule);
console.log('Slideshow:', SlideshowModule);
console.log('Utils:', Utils);

// Check current state
console.log('Is mobile:', Aletheion.state.isMobile);
console.log('Scroll position:', Aletheion.state.scrollPosition);
```

---

## 📱 Responsive Design

Modules automatically detect device type and respond:

```javascript
// Data attribute shows mobile state
<html data-mobile="true">...</html>

// CSS media queries work automatically
// JavaScript detects via Aletheion.state.isMobile
if (Aletheion.state.isMobile) {
    // Mobile-specific code
}
```

---

## ♿ Accessibility

All animations respect user preferences:

```css
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
```

---

## 🚀 Performance Tips

1. **Lazy Load Images**: Use `data-src` attribute
   ```html
   <img data-src="image.jpg" alt="Image">
   ```

2. **Throttle Scroll Events**: Already built into main.js
   ```javascript
   // Scroll events are throttled to 100ms
   ```

3. **Debounce Resize**: Already built into main.js
   ```javascript
   // Resize events are debounced to 300ms
   ```

4. **Use requestAnimationFrame**: For smooth animations
   ```javascript
   requestAnimationFrame(() => {
       // Animation code
   });
   ```

---

## 🔗 Dependencies

None! All modules are vanilla JavaScript with no external dependencies.

- No jQuery required
- No framework dependencies
- Works with vanilla HTML/CSS/JS
- Can be integrated with any framework (React, Vue, etc.)

---

## 📝 Examples

### Example 1: Initialize Custom Slideshow
```javascript
const mySlideshow = new SlideshowModule.Slideshow('gallery', {
    auto: true,
    autoDelay: 3000,
    showArrows: true,
    showDots: true
});
```

### Example 2: Manual Animation Trigger
```javascript
const element = document.querySelector('.card');
AnimationsModule.animateCounter(element, 1000);
```

### Example 3: Form Validation
```javascript
if (!Utils.isValidEmail(email)) {
    Aletheion.notify('Invalid email', 'error');
    return;
}
```

### Example 4: Search with Highlight
```javascript
document.querySelector('input').addEventListener('input', (e) => {
    InteractionsModule.performSearch(e.target.value);
});
```

### Example 5: Get Query Parameter
```javascript
const page = Utils.getQueryParam('page');
console.log('Current page:', page);
```

---

## 🎓 Learning Path

1. Start with **main.js** to understand the global structure
2. Explore **utilities.js** for helper functions
3. Use **animations.js** for scroll effects
4. Add **interactions.js** for user feedback
5. Implement **slideshow.js** for image galleries

---

## 📞 Support

For issues or questions:
1. Check browser console for error messages
2. Verify all scripts are loaded in correct order
3. Ensure HTML has required classes/attributes
4. Test in modern browsers (Chrome, Firefox, Safari, Edge)

---

## 📄 License

Part of Project Aletheion - Academic Digital Museum
