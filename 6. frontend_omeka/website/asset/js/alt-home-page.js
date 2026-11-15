// ============================================
    // PRELOADER
    // ============================================
    const preloader = document.getElementById('preloader');
    const preloaderLogo = document.getElementById('preloader-logo');
    const preloaderTitle = document.getElementById('preloader-title');
    const preloaderSubtitle = document.getElementById('preloader-subtitle');
    const loadingDots = document.querySelector('.loading-dots');

    if (preloader && !document.documentElement.classList.contains('skip-intro')) {
      setTimeout(() => {
        loadingDots.style.display = 'none';
        preloaderLogo.classList.add('move-up');
        preloaderTitle.classList.add('visible');
        preloaderSubtitle.classList.add('visible');
      }, 2000);

      setTimeout(() => {
        preloader.classList.add('hidden');
      }, 4500);
    }

    // ============================================
    // HERO GRID SLIDESHOW
    // ============================================
    const heroGrid = document.querySelector('.hero-grid');
    const slideshowImages = [
      '../asset/img/slideshow2/1022.avif',
      '../asset/img/slideshow2/1275.avif',
      '../asset/img/slideshow2/1816.avif',
      '../asset/img/slideshow2/1878.avif',
      '../asset/img/slideshow2/2980.avif',
      '../asset/img/slideshow2/3209.avif',
      '../asset/img/slideshow2/3914.avif',
      '../asset/img/slideshow2/4378.avif',
      '../asset/img/slideshow2/4723.avif',
      '../asset/img/slideshow2/5460.avif',
      '../asset/img/slideshow2/5485.avif',
      '../asset/img/slideshow2/5567.avif'
    ];

    // Shuffle array for random order
    function shuffleArray(arr) {
      const shuffled = [...arr];
      for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      return shuffled;
    }

    const shuffledImages = shuffleArray(slideshowImages);
    let currentSlideIndex = 0;
    let slideshowInterval;

    function createSlideElement(imagePath) {
      const img = document.createElement('div');
      img.className = 'slideshow-image';
      img.style.backgroundImage = `url('${imagePath}')`;
      return img;
    }

    function showNextSlide() {
      // Remove all old images
      heroGrid.querySelectorAll('.slideshow-image').forEach(el => el.remove());
      
      // Create and add new image
      const newImage = createSlideElement(shuffledImages[currentSlideIndex]);
      heroGrid.appendChild(newImage);
      
      // Trigger animation
      newImage.offsetHeight; // Force reflow
      newImage.classList.add('active');
      
      // Move to next image
      currentSlideIndex = (currentSlideIndex + 1) % shuffledImages.length;
    }

    // Initialize slideshow
    showNextSlide();
    slideshowInterval = setInterval(showNextSlide, 5000);

    // ============================================
    // 2.5D MOUSE PARALLAX
    // ============================================
    const hero = document.getElementById('hero');
    const parallaxLayers = document.querySelectorAll('.parallax-layer');
    let mouseX = 0;
    let mouseY = 0;
    let currentX = 0;
    let currentY = 0;

    hero.addEventListener('mousemove', (e) => {
      const rect = hero.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      mouseX = (e.clientX - rect.left - centerX) / centerX;
      mouseY = (e.clientY - rect.top - centerY) / centerY;
    });

    function animateParallax() {
      currentX += (mouseX - currentX) * 0.1;
      currentY += (mouseY - currentY) * 0.1;

      parallaxLayers.forEach(layer => {
        const depth = parseFloat(layer.dataset.depth) || 0;
        const moveX = currentX * depth * 50;
        const moveY = currentY * depth * 50;
        layer.style.transform = `translate3d(${moveX}px, ${moveY}px, 0)`;
      });

      requestAnimationFrame(animateParallax);
    }

    animateParallax();

    // ============================================
    // SCROLL-LINKED PHOTO ANIMATION
    // ============================================
    const scalePhoto = document.getElementById('scale-photo');
    const overlayText = document.getElementById('overlay-text');
    const scrollPhotoSection = document.getElementById('scroll-photo');

    function updateScrollPhoto() {
      const rect = scrollPhotoSection.getBoundingClientRect();
      const scrollProgress = Math.max(0, Math.min(1, -rect.top / (rect.height - window.innerHeight)));
      
      // Scale from 1 to 1.5
      const scale = 1 + scrollProgress * 0.5;
      scalePhoto.style.transform = `scale(${scale})`;
      
      // Opacity mapping
      const opacityStart = 0.3;
      const opacityEnd = 0.8;
      const opacity = Math.max(0, Math.min(1, (scrollProgress - opacityStart) / (opacityEnd - opacityStart)));
      overlayText.style.opacity = opacity;
      // update which slide is shown based on progress
      if (typeof setScrollPhotoByProgress === 'function') setScrollPhotoByProgress(scrollProgress);
    }

    // Build slideshow array (slide1..slide17) and initialize thumbnails
    const slides = Array.from({length: 17}, (_, i) => `../asset/img/slideshow/slide${i+1}.jpg`);

    function clamp(v, a = 0, b = 1) { return Math.max(a, Math.min(b, v)); }

    function setScrollPhotoByProgress(progress) {
      const idx = Math.floor(clamp(progress, 0, 1) * (slides.length - 1));
      if (slides[idx]) {
        scalePhoto.style.backgroundImage = `url('${slides[idx]}')`;
        scalePhoto.style.opacity = '1';
      }
    }

    // initialize film thumbnails from data-image or fallback to slides
    document.querySelectorAll('.film-image').forEach((el, i) => {
      const img = el.dataset.image || slides[i] || slides[0];
      el.style.backgroundImage = `url('${img}')`;
      el.style.backgroundSize = 'cover';
      el.style.backgroundPosition = 'center';
    });

    // set initial scroll-photo background
    setScrollPhotoByProgress(0);

    window.addEventListener('scroll', () => {
      updateScrollPhoto();
      // also update slide based on scroll progress inside updateScrollPhoto
    });

    // ============================================
    // INVESTIGATIVE STRING ANIMATION
    // ============================================
    const stringPath = document.getElementById('string-path');
    const pathLength = stringPath.getTotalLength();
    stringPath.style.strokeDasharray = pathLength;
    stringPath.style.strokeDashoffset = pathLength;

    const timelineItems = document.querySelectorAll('.timeline-item');

    function updateTimeline() {
      const timelineSection = document.getElementById('timeline');
      const rect = timelineSection.getBoundingClientRect();
      const scrollProgress = Math.max(0, Math.min(1, -rect.top / (rect.height - window.innerHeight)));
      
      // Draw the string
      const drawLength = pathLength * scrollProgress;
      stringPath.style.strokeDashoffset = pathLength - drawLength;

      // Reveal timeline items
      timelineItems.forEach((item, index) => {
        const itemRect = item.getBoundingClientRect();
        const isVisible = itemRect.top < window.innerHeight * 0.8;
        if (isVisible) {
          item.classList.add('visible');
        }
      });
    }

    window.addEventListener('scroll', updateTimeline);

    // ============================================
    // SCROLL ANIMATIONS FOR TIMELINE
    // ============================================
    const observerOptions = {
      threshold: 0.2,
      rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, observerOptions);

    timelineItems.forEach(item => observer.observe(item));

    // ============================================
    // COLLAGE PARALLAX (scroll-linked subtle motion)
    // ============================================
    const collageWraps = Array.from(document.querySelectorAll('.collage-wrap'));
    const sectionsWithCollage = new Set(collageWraps.map(i => i.closest('section')));

    let ticking = false;
    function updateCollageParallax() {
      sectionsWithCollage.forEach(section => {
        if (!section) return;
        const rect = section.getBoundingClientRect();
        const height = Math.max(rect.height, window.innerHeight);
        const progress = (window.innerHeight - rect.top) / (height + window.innerHeight);
        // progress roughly 0..1 while section near viewport
        section.querySelectorAll('.collage-wrap').forEach(wrap => {
          const speed = parseFloat(wrap.dataset.speed || '0.12');
          // center-based motion: negative when scrolling down so images lag
          const centered = (rect.top + rect.height/2 - window.innerHeight/2) / (window.innerHeight/2);
          const dy = Math.round(centered * -1 * speed * 48); // px, slightly more range
          wrap.style.setProperty('--dy', dy + 'px');
        });
      });
      ticking = false;
    }

    function onScrollCollage() {
      if (!ticking) {
        window.requestAnimationFrame(updateCollageParallax);
        ticking = true;
      }
    }

    window.addEventListener('scroll', onScrollCollage, { passive: true });
    // one initial update
    updateCollageParallax();
