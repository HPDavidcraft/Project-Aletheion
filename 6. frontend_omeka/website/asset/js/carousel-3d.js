/**
 * 3D RADIAL CAROUSEL GALLERY
 * Physics-based navigation with modal expansion
 */

(() => {
  'use strict';

  const PLACEHOLDER_DESCRIPTION = 'Demonstration image only; no canonical Pleroma record is linked. Catalog description, date, location, rights, provenance, citation, and uncertainty metadata are placeholders.';
  const FALLBACK_GALLERY_DATA = [
    '56456apsdl.jpg',
    '201700fgsdl.jpg',
    '201701fgsdl.jpg',
    '246484fgsdl.jpg',
    '302127rgsdl.jpg',
    '400398mtsdl.jpg'
  ].map((filename, index) => ({
    title: `Demo image ${String(index + 1).padStart(2, '0')}`,
    location: 'Location metadata not supplied',
    image: `../asset/img/${filename}`,
    description: PLACEHOLDER_DESCRIPTION
  }));

  class RadialCarousel3D {
    constructor(container) {
      this.container = container;
      this.section = container.closest('.radial-carousel-section') || document;
      this.interactionArea = this.section.querySelector('.radial-carousel-container') || container;
      this.track = container.querySelector('.radial-carousel-track');
      this.sourceItems = Array.from(document.querySelectorAll('[data-gallery-image]'));
      this.data = this.createGalleryData();
      this.cards = [];
      this.currentIndex = 0;
      this.targetRotation = 0;
      this.currentRotation = 0;
      this.velocity = 0;
      this.wheelAccumulated = 0;
      this.wheelLockUntil = 0;
      this.isDragging = false;
      this.dragStartX = null;
      this.dragStartRotation = 0;
      this.lastDragX = 0;
      this.lastDragTime = Date.now();
      this.rafId = null;
      this.dragThreshold = 5; // pixels - minimum movement to be considered a drag
      this.hasMoved = false; // track if significant movement occurred
      this.dragStartTime = 0; // track when drag started for click detection
      
      // Physics constants
      this.damping = 0.92;
      this.snapThreshold = 0.5;
      this.rotationPerItem = 360 / this.data.length;
      
      // Modal state
      this.isModalOpen = false;
      this.modalOverlay = this.section.querySelector('.carousel-modal-overlay');
      this.modalImage = this.section.querySelector('.carousel-modal-image');
      this.infographicPanel = this.section.querySelector('.carousel-infographic-panel');
      this.titleDisplay = this.section.querySelector('.carousel-title-display');
      if (this.modalOverlay) this.modalOverlay.tabIndex = -1;
      
      this.init();
    }

    createGalleryData() {
      const items = this.sourceItems.map((item, index) => {
        const image = item.querySelector('img');
        const imagePath = image?.currentSrc || image?.src || item.querySelector('.film-image')?.dataset.image;
        if (!imagePath) return null;
        return {
          title: item.dataset.title || `Demo image ${String(index + 1).padStart(2, '0')}`,
          location: item.dataset.location || 'Location metadata not supplied',
          image: new URL(imagePath, document.baseURI).href,
          description: item.dataset.description || PLACEHOLDER_DESCRIPTION
        };
      }).filter(Boolean);

      return items.length ? items : FALLBACK_GALLERY_DATA;
    }

    init() {
      if (this.modalOverlay) document.body.appendChild(this.modalOverlay);
      this.createCards();
      this.attachEventListeners();
      this.sourceItems.forEach((item, index) => {
        item.addEventListener('click', () => this.openModal(index));
      });
      this.updateCards();
      this.updateHeroIndex(); // Initialize hero detection
      this.updateTitleDisplay(); // Set initial title
      this.startAnimationLoop();
      console.log('Radial Carousel 3D initialized with', this.cards.length, 'cards');
    }

    createCards() {
      this.data.forEach((data, index) => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'carousel-card';
        card.dataset.index = index;
        card.dataset.title = data.title;
        card.dataset.location = data.location;
        card.dataset.description = data.description;
        card.setAttribute('aria-label', `View ${data.title}`);
        const inner = document.createElement('span');
        inner.className = 'carousel-card__inner';
        const image = document.createElement('img');
        image.className = 'carousel-card__image';
        image.src = data.image;
        image.alt = '';
        image.loading = 'lazy';
        const expandLabel = document.createElement('span');
        expandLabel.className = 'carousel-card__expand-label';
        expandLabel.textContent = 'View image';
        inner.append(image, expandLabel);
        card.appendChild(inner);
        this.track.appendChild(card);
        this.cards.push(card);
      });
    }

    attachEventListeners() {
      // Scroll navigation
      this.interactionArea.addEventListener('wheel', this.handleWheel.bind(this), { passive: false });
      
      // Drag navigation
      this.interactionArea.addEventListener('mousedown', this.handleDragStart.bind(this));
      this.interactionArea.addEventListener('touchstart', this.handleDragStart.bind(this), { passive: true });
      
      document.addEventListener('mousemove', this.handleDragMove.bind(this));
      document.addEventListener('touchmove', this.handleDragMove.bind(this), { passive: true });
      
      document.addEventListener('mouseup', this.handleDragEnd.bind(this));
      document.addEventListener('touchend', this.handleDragEnd.bind(this));
      
      // Card click for modal: entire card is a hitbox
      this.cards.forEach(card => {
        card.addEventListener('click', (e) => {
          // Prevent any default behavior that might cause scrolling
          e.preventDefault();
          e.stopPropagation();
          
          // Open modal for any card click if the user didn't perform a drag
          if (!this.hasMoved) {
            const idx = parseInt(card.dataset.index);
            this.openModal(idx);
          }
        });
      });
      
      // Modal zone clicks
      this.modalOverlay?.querySelector('[data-gallery-prev]')?.addEventListener('click', () => this.navigateModal(-1));
      this.modalOverlay?.querySelector('[data-gallery-next]')?.addEventListener('click', () => this.navigateModal(1));
      this.modalOverlay?.querySelector('[data-gallery-close]')?.addEventListener('click', () => this.closeModal());
      this.modalOverlay?.addEventListener('click', event => {
        if (event.target === this.modalOverlay) this.closeModal();
      });
      
      // Escape key to close modal
      document.addEventListener('keydown', (e) => {
        if (this.isModalOpen && e.key === 'Escape') {
          this.closeModal();
          return;
        }
        if (this.isModalOpen && e.key === 'ArrowLeft') {
          this.navigateModal(-1);
          return;
        }
        if (this.isModalOpen && e.key === 'ArrowRight') {
          this.navigateModal(1);
          return;
        }

        if (this.isModalOpen || e.repeat || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
        if (e.target instanceof Element && e.target.closest('input, textarea, select, [contenteditable="true"], .site-header')) return;
        const bounds = this.section.getBoundingClientRect();
        if (bounds.bottom <= 0 || bounds.top >= window.innerHeight) return;
        e.preventDefault();
        this.stepCarousel(e.key === 'ArrowRight' ? 1 : -1);
      });
    }

    handleWheel(e) {
      if (this.isModalOpen) return;
      const delta = e.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? e.deltaY * 16
        : e.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? e.deltaY * window.innerHeight
          : e.deltaY;
      if (!delta) return;
      e.preventDefault();
      const now = Date.now();
      if (now < this.wheelLockUntil) return;
      this.wheelAccumulated += delta;
      if (Math.abs(this.wheelAccumulated) < 40) return;
      this.stepCarousel(Math.sign(this.wheelAccumulated));
      this.wheelAccumulated = 0;
      this.wheelLockUntil = now + 380;
    }

    stepCarousel(direction) {
      if (!direction) return;
      const currentStep = Math.round(this.targetRotation / this.rotationPerItem);
      this.targetRotation = (currentStep + direction) * this.rotationPerItem;
      this.velocity = 0;
    }

    handleDragStart(e) {
      if (this.isModalOpen) return;
      
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      this.dragStartX = clientX;
      this.lastDragX = clientX;
      this.dragStartRotation = this.currentRotation;
      this.dragStartTime = Date.now();
      this.lastDragTime = Date.now();
      this.velocity = 0;
      this.hasMoved = false;
      // Don't set isDragging true yet - wait for movement threshold
    }

    handleDragMove(e) {
      // Check if user started a potential drag
      if (this.dragStartX === null) return;
      
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const deltaX = clientX - this.dragStartX;
      const deltaTime = Date.now() - this.dragStartTime;
      
      // Only start dragging if movement exceeds threshold AND enough time has passed
      // Quick movements within 150ms are likely clicks, not drags
      if (!this.isDragging && (Math.abs(deltaX) > this.dragThreshold && deltaTime > 150)) {
        this.isDragging = true;
        this.hasMoved = true;
        this.interactionArea.style.cursor = 'grabbing';
      }
      
      if (!this.isDragging) return;
      
      const dragDeltaTime = Date.now() - this.lastDragTime;
      
      // Calculate velocity for inertia
      if (dragDeltaTime > 0) {
        const instantVelocity = (clientX - this.lastDragX) / dragDeltaTime * 10;
        this.velocity = instantVelocity;
      }
      
      // Translate horizontal drag to rotation (inverted)
      this.targetRotation = this.dragStartRotation - deltaX * 0.5;
      
      this.lastDragX = clientX;
      this.lastDragTime = Date.now();
    }

    handleDragEnd() {
      // Reset drag tracking
      const wasNotDragging = !this.hasMoved;
      
      this.isDragging = false;
      this.dragStartX = null;
      this.interactionArea.style.cursor = '';
      
      // Reset hasMoved after a short delay to allow click handler to check it
      setTimeout(() => {
        this.hasMoved = false;
      }, 50);
      
      // Apply inertia
      // Velocity will naturally decay via damping in animation loop
      
      // Return whether this was a click (not a drag)
      return wasNotDragging;
    }

    startAnimationLoop() {
      const animate = () => {
        // Apply velocity to target rotation
        if (!this.isDragging) {
          this.targetRotation += this.velocity;
          this.velocity *= this.damping;
          
          // Snap to nearest item when velocity is low
          if (Math.abs(this.velocity) < this.snapThreshold) {
            const nearestIndex = Math.round(this.targetRotation / this.rotationPerItem);
            const snapRotation = nearestIndex * this.rotationPerItem;
            const diff = snapRotation - this.targetRotation;
            
            if (Math.abs(diff) < 30) {
              this.targetRotation += diff * 0.1;
            }
          }
        }
        
        // Smooth interpolation to target
        this.currentRotation += (this.targetRotation - this.currentRotation) * 0.1;
        
        // Update visuals
        this.updateCards();
        this.updateHeroIndex();
        
        this.rafId = requestAnimationFrame(animate);
      };
      
      animate();
    }

    updateCards() {
      const radius = 800; // Distance from center
      const arcHeight = 200; // Vertical arc offset

      const positions = this.cards.map((card, index) => {
        let angle = (index * this.rotationPerItem - this.currentRotation) * (Math.PI / 180);
        angle = Math.atan2(Math.sin(angle), Math.cos(angle));
        return {
          card,
          angle,
          x: Math.sin(angle) * radius,
          y: Math.abs(Math.sin(angle)) * arcHeight,
          z: Math.cos(angle) * radius - radius,
          distanceFromCenter: Math.abs(angle)
        };
      });
      if (!positions.length) return;

      const heroPosition = positions.reduce((closest, position) =>
        position.distanceFromCenter < closest.distanceFromCenter ? position : closest
      );

      positions.forEach(({ card, angle, x, y, z }) => {
        const isHero = card === heroPosition.card;
        const rotY = -angle * (180 / Math.PI);
        const rotZ = Math.sin(angle) * 5;
        const frontZ = z + (isHero ? 180 : 0);

        card.style.zIndex = isHero ? '10000' : '1';
        card.style.transform = `
          translate3d(${x}px, ${y}px, ${frontZ}px)
          rotateY(${rotY}deg)
          rotateZ(${rotZ}deg)
        `;
        card.classList.toggle('is-hero', isHero);
      });
    }

    updateHeroIndex() {
      // When modal is open, the carousel background should follow modal navigation
      // so we must NOT overwrite `currentIndex` with hero detection during that state.
      if (this.isModalOpen) return;

      // Find the hero card and update title display
      const heroCard = this.track.querySelector('.carousel-card.is-hero');
      if (heroCard) {
        const newIndex = parseInt(heroCard.dataset.index);
        if (newIndex !== this.currentIndex) {
          this.currentIndex = newIndex;
          this.updateTitleDisplay();
          console.log('Hero card changed to:', this.data[newIndex].title);
        }
      }
    }

    updateTitleDisplay() {
      const data = this.data[this.currentIndex];
      const titleEl = this.titleDisplay?.querySelector('.carousel-active-title');
      const locationEl = this.titleDisplay?.querySelector('.carousel-active-location');
      if (!titleEl || !locationEl || !data) return;
      
      // Fade out, update, fade in
      titleEl.style.opacity = '0';
      locationEl.style.opacity = '0';
      
      setTimeout(() => {
        titleEl.textContent = data.title;
        locationEl.textContent = data.location;
        titleEl.style.opacity = '1';
        locationEl.style.opacity = '1';
      }, 150);
    }

    openModal(index) {
      if (index < 0 || index >= this.data.length || !this.modalOverlay || !this.modalImage || !this.infographicPanel) return;
      this.isModalOpen = true;
      this.currentIndex = index;
      this.lastFocusElement = document.activeElement;
      const data = this.data[index];
      
      // Set modal content
      this.modalImage.src = data.image;
      this.modalImage.alt = data.title;
      
      // Set infographic content
      this.infographicPanel.querySelector('.infographic-title').textContent = data.title;
      this.infographicPanel.querySelector('.infographic-location').textContent = data.location;
      this.infographicPanel.querySelector('.infographic-body').textContent = data.description;
      
      // Show modal (add small delay to ensure image loads)
      requestAnimationFrame(() => {
        this.modalOverlay.classList.add('is-active');
        // Move focus to the modal for accessibility
        try { this.modalOverlay.focus(); } catch (e) { /* ignore */ }
      });

      // Rotate the background carousel to center the clicked card
      // Use negative because rotation direction maps that way in update logic
      this.targetRotation = -index * this.rotationPerItem;

      // Hide carousel title during modal
      if (this.titleDisplay) this.titleDisplay.style.opacity = '0';
      
      // Add modal-open class to body for global header suppression
      document.body.classList.add('modal-open');
      
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    }

    closeModal() {
      if (!this.isModalOpen) return;
      this.isModalOpen = false;
      this.modalOverlay.classList.remove('is-active');
      
      // Show carousel title
      if (this.titleDisplay) this.titleDisplay.style.opacity = '1';
      
      // Remove modal-open class from body
      document.body.classList.remove('modal-open');
      
      // Restore body scroll
      document.body.style.overflow = '';
      this.lastFocusElement?.focus();
    }

    navigateModal(direction) {
      // Navigate to prev/next image without closing modal
      this.currentIndex = (this.currentIndex + direction + this.data.length) % this.data.length;
      const data = this.data[this.currentIndex];
      
      // Fade out current image
      this.modalImage.style.opacity = '0';
      
      setTimeout(() => {
        // Update content
        this.modalImage.src = data.image;
        this.modalImage.alt = data.title;
        this.infographicPanel.querySelector('.infographic-title').textContent = data.title;
        this.infographicPanel.querySelector('.infographic-location').textContent = data.location;
        this.infographicPanel.querySelector('.infographic-body').textContent = data.description;
        
        // Fade in new image
        setTimeout(() => {
          this.modalImage.style.opacity = '1';
        }, 50);
      }, 300);
      
      // Also update carousel position in background. Force the background to
      // animate toward the modal index and clear velocity so the interpolation
      // produces a consistent scroll while in fullscreen.
      this.targetRotation = -this.currentIndex * this.rotationPerItem;
      this.velocity = 0;
      // Ensure the animation loop will move the visual carousel toward targetRotation
      // (currentRotation is interpolated toward targetRotation in the animation loop).
    }

    destroy() {
      if (this.rafId) {
        cancelAnimationFrame(this.rafId);
      }
    }
  }

  // Initialize when DOM is ready
  function init() {
    const carouselContainer = document.querySelector('.radial-carousel-section');
    if (carouselContainer) {
      window.radialCarousel3D = new RadialCarousel3D(carouselContainer);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
