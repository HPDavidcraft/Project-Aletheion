// GSAP ScrollTrigger Logic
        gsap.registerPlugin(ScrollTrigger);

        const scrollContainer = document.querySelector('.scroll-container');
        const horizontalStrip = document.querySelector('.horizontal-strip');

        function initScroll() {
            // Calculate total width of the strip
            const getScrollAmount = () => {
                let stripWidth = horizontalStrip.scrollWidth;
                return -(stripWidth - window.innerWidth);
            };

            // Horizontal Scroll Tween
            gsap.to(horizontalStrip, {
                x: getScrollAmount,
                ease: 'none',
                scrollTrigger: {
                    trigger: scrollContainer,
                    start: 'top top',
                    end: () => `+=${getScrollAmount() * -1}`, // Scroll distance equals translation distance
                    pin: true,
                    scrub: 1, // Smooth scrubbing
                    invalidateOnRefresh: true,
                    anticipatePin: 1
                }
            });
        }

        window.addEventListener('load', initScroll);
        window.addEventListener('resize', () => ScrollTrigger.refresh());

        // Wheel to Scroll mapping for horizontal experience
        window.addEventListener("wheel", (evt) => {
            // Only map vertical scroll to horizontal if we are PINNED or explicitly handling it.
            // With GSAP 'scrub', the native vertical scrollbar controls the animation.
            // No custom JS needed for wheel mapping if body height is set correctly by ScrollTrigger.
        });
