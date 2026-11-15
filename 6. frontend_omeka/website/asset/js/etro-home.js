/**
 * ETRO HOME — Immersive Scroll Experience
 * Custom cursor, horizontal scroll jacking, kinetic typography,
 * parallax masking, text reveal animations, Lenis-like smoothing
 */

(() => {
  'use strict';

  // =========================================================
  // 1. SMOOTH SCROLL ENGINE (Lenis-inspired)
  // =========================================================
  class SmoothScroll {
    constructor() {
      this.current = window.scrollY;
      this.target = window.scrollY;
      this.ease = 0.08;
      this.running = false;
      this.callbacks = [];
    }

    init() {
      this.running = true;
      this.tick();
    }

    onScroll(cb) {
      this.callbacks.push(cb);
    }

    tick() {
      if (!this.running) return;
      this.target = window.scrollY;
      this.current += (this.target - this.current) * this.ease;

      // fire scroll callbacks with interpolated value
      this.callbacks.forEach(cb => cb(this.current, this.target));

      requestAnimationFrame(() => this.tick());
    }

    destroy() {
      this.running = false;
      this.callbacks = [];
    }
  }

  // =========================================================
  // 2. CUSTOM CURSOR
  // =========================================================
  class CustomCursor {
    constructor() {
      this.el = null;
      this.pos = { x: 0, y: 0 };
      this.mouse = { x: 0, y: 0 };
      this.speed = 0.15;
      this.running = false;
    }

    init() {
      if (window.innerWidth < 769) return;

      this.el = document.createElement('div');
      this.el.className = 'custom-cursor';
      document.body.appendChild(this.el);

      document.addEventListener('mousemove', e => {
        this.mouse.x = e.clientX;
        this.mouse.y = e.clientY;
      }, { passive: true });

      // Hover targets
      const hoverTargets = 'a, button, .etro-btn, .fabric-card, [data-cursor="hover"]';
      document.addEventListener('mouseover', e => {
        if (e.target.closest(hoverTargets)) {
          this.el.classList.add('cursor-hover');
        }
      });
      document.addEventListener('mouseout', e => {
        if (e.target.closest(hoverTargets)) {
          this.el.classList.remove('cursor-hover');
        }
      });

      // Hide when leaving window
      document.addEventListener('mouseleave', () => {
        this.el.classList.add('cursor-hidden');
      });
      document.addEventListener('mouseenter', () => {
        this.el.classList.remove('cursor-hidden');
      });

      this.running = true;
      this.render();
    }

    render() {
      if (!this.running) return;
      this.pos.x += (this.mouse.x - this.pos.x) * this.speed;
      this.pos.y += (this.mouse.y - this.pos.y) * this.speed;
      this.el.style.transform = `translate(${this.pos.x}px, ${this.pos.y}px) translate(-50%, -50%)`;
      requestAnimationFrame(() => this.render());
    }

    destroy() {
      this.running = false;
      if (this.el) this.el.remove();
    }
  }

  // =========================================================
  // 3. TEXT REVEAL OBSERVER
  // =========================================================
  function initRevealObserver() {
    const reveals = document.querySelectorAll('.reveal-text');
    if (!reveals.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2, rootMargin: '0px 0px -80px 0px' });

    reveals.forEach(el => observer.observe(el));
  }

  // =========================================================
  // 4. HERO — Fixed Background Masking
  // =========================================================
  function initHeroMasking() {
    const heroOverlay = document.querySelector('.etro-hero__overlay');
    const scrollPrompt = document.querySelector('.scroll-prompt');
    if (!heroOverlay) return;

    const heroSpacer = document.querySelector('.hero-spacer');
    if (!heroSpacer) return;

    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      const heroH = window.innerHeight;

      // Fade out hero content & scroll prompt as user scrolls
      const progress = Math.min(scrollY / (heroH * 0.5), 1);
      heroOverlay.style.opacity = 1 - progress;

      if (scrollPrompt) {
        scrollPrompt.style.opacity = scrollY > 80 ? '0' : '0.7';
      }
    }, { passive: true });
  }

  // =========================================================
  // 5. BRAND STATEMENT — Scroll Reveal
  // =========================================================
  function initBrandReveal() {
    const section = document.querySelector('.brand-statement');
    if (!section) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          section.querySelectorAll('.reveal-text').forEach(el => {
            el.classList.add('visible');
          });
          const body = section.querySelector('.brand-statement__body');
          if (body) body.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    observer.observe(section);
  }

  // =========================================================
  // 6. HORIZONTAL SCROLL JACKING
  // =========================================================
  function initHorizontalScroll() {
    const section = document.querySelector('.hscroll-section');
    const track = document.querySelector('.hscroll-track');
    if (!section || !track) return;

    // Calculate required height
    const cards = document.querySelectorAll('.fabric-card');
    const totalCards = cards.length;
    // Each card is 25vw + 10vw margin on desktop
    const cardWidth = window.innerWidth * 0.25;
    const cardGap = window.innerWidth * 0.10;
    const totalTrackWidth = (cardWidth + cardGap) * totalCards + window.innerWidth * 0.85 + window.innerWidth * 0.25;

    // Set section height to control scroll distance
    const scrollDistance = totalTrackWidth - window.innerWidth;
    const sectionHeight = scrollDistance + window.innerHeight;
    section.style.height = sectionHeight + 'px';

    window.addEventListener('scroll', () => {
      const rect = section.getBoundingClientRect();
      const sectionTop = -rect.top;
      const maxScroll = section.offsetHeight - window.innerHeight;

      if (sectionTop < 0 || sectionTop > maxScroll) return;

      const progress = sectionTop / maxScroll;
      const translateX = -progress * scrollDistance;

      track.style.transform = `translateX(${translateX}px)`;
    }, { passive: true });
  }

  // =========================================================
  // 7. COLLECTION SECTIONS — Scroll Reveal
  // =========================================================
  function initCollectionReveal() {
    const sections = document.querySelectorAll('.collection-section');
    if (!sections.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.25 });

    sections.forEach(s => observer.observe(s));
  }

  // =========================================================
  // 8. KINETIC TYPOGRAPHY — Letter Distortion on Scroll
  // =========================================================
  function initKineticType() {
    const headings = document.querySelectorAll('.collection-section__heading');
    headings.forEach(heading => {
      const text = heading.textContent.trim();
      // Wrap each letter in a span, preserve the reveal-text wrapper
      const revealWrap = heading.querySelector('.reveal-text');
      if (!revealWrap) return;

      const originalText = revealWrap.textContent.trim();
      revealWrap.innerHTML = '';

      for (let i = 0; i < originalText.length; i++) {
        const span = document.createElement('span');
        span.className = 'kinetic-letter';
        span.textContent = originalText[i] === ' ' ? '\u00A0' : originalText[i];
        revealWrap.appendChild(span);
      }
    });

    // Animate on scroll: distort letters near viewport center
    let lastScroll = 0;
    let scrollVelocity = 0;

    window.addEventListener('scroll', () => {
      const currentScroll = window.scrollY;
      scrollVelocity = Math.abs(currentScroll - lastScroll);
      lastScroll = currentScroll;

      const letters = document.querySelectorAll('.kinetic-letter');
      const viewCenter = window.innerHeight / 2;

      letters.forEach(letter => {
        const rect = letter.getBoundingClientRect();
        const letterCenter = rect.top + rect.height / 2;
        const distFromCenter = Math.abs(letterCenter - viewCenter);
        const maxDist = window.innerHeight * 0.4;

        if (distFromCenter < maxDist && scrollVelocity > 2) {
          const intensity = 1 - (distFromCenter / maxDist);
          const scaleX = 1 + (intensity * Math.min(scrollVelocity * 0.02, 0.6));
          letter.style.transform = `scaleX(${scaleX})`;
          letter.style.transition = 'transform 0.1s ease';
        } else {
          letter.style.transform = 'scaleX(1)';
          letter.style.transition = 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
        }
      });
    }, { passive: true });
  }

  // =========================================================
  // 9. FOOTER HEIGHT VARIABLE
  // =========================================================
  function initFooterHeight() {
    const footer = document.querySelector('.etro-footer-new');
    const spacer = document.querySelector('.footer-spacer');
    if (!footer || !spacer) return;

    function update() {
      const h = footer.offsetHeight;
      document.body.style.setProperty('--footer-height', h + 'px');
      spacer.style.height = h + 'px';
    }

    update();
    window.addEventListener('resize', update);

    // Footer is now positioned with CSS `position: sticky`.
    // Keep a spacer with the same height so the footer appears in-place when scrolling.
    // Ensure no inline transform is applied and remove reveal class state.
    footer.style.transform = 'none';
    footer.classList.remove('revealed');
  }

  // =========================================================
  // 9b. FOOTER MIDWAY VISIBILITY — show only after page midpoint
  // =========================================================
  function initFooterMidwayVisibility() {
    const footer = document.querySelector('.etro-footer-new');
    if (!footer) return;

    // Compute trigger: half of total scrollable distance
    function computeTrigger() {
      const doc = document.documentElement;
      const scrollable = Math.max(0, doc.scrollHeight - window.innerHeight);
      return scrollable / 2;
    }

    let trigger = computeTrigger();

    // Toggle class based on current scrollY
    function check() {
      if (window.scrollY >= trigger) {
        footer.classList.add('mid-visible');
      } else {
        footer.classList.remove('mid-visible');
      }
    }

    // RAF-throttled scroll listener
    let ticking = false;
    window.addEventListener('scroll', () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(() => {
          check();
          ticking = false;
        });
      }
    }, { passive: true });

    // Recompute on resize (and run once)
    window.addEventListener('resize', () => {
      trigger = computeTrigger();
      check();
    });

    // Initial state
    check();
  }

  // =========================================================
  // 10. HERO TEXT ENTRANCE (Staggered)
  // =========================================================
  function initHeroEntrance() {
    // Delayed reveal of hero text elements
    const heroReveals = document.querySelectorAll('.etro-hero .reveal-text');
    setTimeout(() => {
      heroReveals.forEach((el, i) => {
        setTimeout(() => el.classList.add('visible'), i * 200);
      });
    }, 300);
  }

  // =========================================================
  // 11. HEADER SCROLL EFFECT (keep existing)
  // =========================================================
  function initHeaderScroll() {
    const header = document.querySelector('header');
    if (!header) return;

    window.addEventListener('scroll', () => {
      if (window.scrollY > 50) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
    }, { passive: true });
  }

  // =========================================================
  // INITIALIZATION
  // =========================================================
  function init() {
    document.body.classList.add('etro-home');

    // Core systems
    const cursor = new CustomCursor();
    cursor.init();

    // Hero
    initHeroEntrance();
    initHeroMasking();

    // Scroll reveals
    initRevealObserver();
    initBrandReveal();

    // Horizontal scroll
    initHorizontalScroll();

    // Collections
    initCollectionReveal();
    initKineticType();

    // Footer
    initFooterHeight();
    // Only reveal footer after user scrolls past page midpoint
    initFooterMidwayVisibility();

    // Header
    initHeaderScroll();

    // Hide loader if present
    const loader = document.getElementById('page-loader');
    if (loader) loader.style.display = 'none';

    console.log('Etro Home experience initialized');
  }

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Recalculate on resize
  window.addEventListener('resize', () => {
    // Recalculate horizontal scroll heights
    initHorizontalScroll();
  });

})();
