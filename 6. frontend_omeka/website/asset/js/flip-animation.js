/**
 * FLIP TECHNIQUE - PROJECT DETAIL VIEW ANIMATION
 * ================================================
 * First: Calculate initial state (thumbnail position)
 * Last: Calculate final state (fullscreen position)
 * Invert: Create clone at initial position
 * Play: Animate clone to final position using GSAP
 */

// --- STATE MANAGEMENT ---
let isAnimating = false;
let currentProjectData = null;

// --- PROJECT DATA CONFIGURATION ---
// Map section IDs to their project metadata
const projectData = {
    'section_reuters_news': {
        title: 'Reuters News',
        titleZh: '路透社',
        year: '2024',
        role: 'Product Design',
        client: 'Reuters',
        description: 'Working closely with Reuters, we wanted to rethink how news on mobile should be presented and delivered. The result is a customizable experience that allows users to focus on the areas of their interests.',
        extended: 'The architectural strategy involved a comprehensive audit of the existing digital infrastructure, followed by a rigorous restructuring of the information hierarchy. We focused on creating a seamless experience that prioritizes content while maintaining brand identity.'
    },
    'section_chan_eayrs': {
        title: 'Chan + Eayrs',
        titleZh: '',
        year: '2023',
        role: 'Design & Development',
        client: 'Chan + Eayrs',
        description: 'A comprehensive digital identity system for the contemporary architecture studio Chan + Eayrs, emphasizing spatial awareness and material clarity.',
        extended: 'The project included brand strategy, visual identity, and a custom-built portfolio platform that showcases their architectural work through an innovative interface.'
    },
    'section_cowboy': {
        title: 'Cowboy Bike',
        titleZh: '',
        year: '2023',
        role: 'Branding',
        client: 'Cowboy',
        description: 'Creating a bold visual language for the next generation of electric bicycles, blending European design sensibility with digital innovation.',
        extended: 'The brand identity extends across physical and digital touchpoints, from product packaging to the companion mobile application.'
    },
    'section_campbell_rey': {
        title: 'Campbell—Rey',
        titleZh: '',
        year: '2022',
        role: 'Design & Development',
        client: 'Campbell—Rey',
        description: 'A refined digital experience for the luxury watch dealer, focusing on editorial presentation and sophisticated typography.',
        extended: 'The platform emphasizes the craftsmanship and heritage of each timepiece through careful photography direction and responsive design principles.'
    },
    'section_rtv': {
        title: 'Reuters TV',
        titleZh: '',
        year: '2023',
        role: 'Product Design',
        client: 'Reuters',
        description: 'Reimagining video news consumption for mobile devices with an emphasis on personalization and content discovery.',
        extended: 'The interface design prioritizes gesture-based navigation and adaptive streaming quality for various network conditions.'
    }
};

// --- DOM ELEMENT REFERENCES ---
let detailView;
let heroContainer;
let detailContent;
let allWorkSections;

// --- INITIALIZATION ---
function initFlipAnimation() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupFlipAnimation);
    } else {
        setupFlipAnimation();
    }
}

function setupFlipAnimation() {
    // Get DOM references
    detailView = document.querySelector('.project-detail-view');
    heroContainer = document.querySelector('.hero-image-container');
    detailContent = document.querySelector('.detail-content');
    
    if (!detailView || !heroContainer || !detailContent) {
        console.warn('FLIP Animation: Required DOM elements not found');
        return;
    }

    // Select all clickable work media elements
    allWorkSections = document.querySelectorAll('.Work');
    
    // Attach click listeners to Work__Media links
    allWorkSections.forEach(section => {
        const mediaLink = section.querySelector('.Work__Media');
        if (mediaLink) {
            mediaLink.addEventListener('click', function(e) {
                e.preventDefault(); // Prevent default link behavior
                e.stopPropagation();
                
                if (isAnimating) return; // Prevent double clicks
                
                // Get section ID to retrieve project data
                const sectionId = section.id;
                const projectInfo = projectData[sectionId];
                
                if (!projectInfo) {
                    console.warn(`No project data found for ${sectionId}`);
                    return;
                }
                
                // Try to find an image - check for background image or img element
                let imgSource = null;
                const imgElement = mediaLink.querySelector('img');
                
                if (imgElement) {
                    imgSource = imgElement.src;
                } else {
                    // Check for background image in computed styles
                    const bgImage = window.getComputedStyle(mediaLink).backgroundImage;
                    if (bgImage && bgImage !== 'none') {
                        imgSource = bgImage.replace(/url\(['"]?(.*?)['"]?\)/i, '$1');
                    }
                }
                
                // If no image found, abort — require the new images to be present
                if (!imgSource || imgSource === 'none') {
                    console.warn('FLIP Animation: no image found for this work section (expected background-image or <img>)', section.id || sectionId);
                    return; // Do not proceed without the specified image
                }
                
                // Store project data
                currentProjectData = projectInfo;
                
                // Debug: log resolved image source to help verify loading
                try {
                    console.log('FLIP debug - resolved image source for', section.id || sectionId, ':', imgSource);
                } catch (err) {
                    console.log('FLIP debug - resolved image source:', imgSource);
                }

                // Execute the FLIP transition
                openProjectAnimation(mediaLink, imgSource, projectInfo);
            });
        }
    });
    
    console.log('FLIP Animation initialized:', allWorkSections.length, 'work sections found');
}

// --- MAIN ANIMATION FUNCTION ---
function openProjectAnimation(originElement, imgSrc, projectInfo) {
    isAnimating = true;

    // Hide header during fullscreen view
    const header = document.querySelector('header');
    if (header) header.style.display = 'none';

    // A. GET COORDINATES (First)
    // Calculate where the element is currently on the screen
    const rect = originElement.getBoundingClientRect();

    // B. CREATE THE CLONE (Invert)
    // Create a temporary element that will animate from thumbnail to fullscreen
    const clone = document.createElement('div');
    clone.style.position = 'fixed';
    clone.style.top = `${rect.top}px`;
    clone.style.left = `${rect.left}px`;
    clone.style.width = `${rect.width}px`;
    clone.style.height = `${rect.height}px`;
    clone.style.zIndex = '999';
    clone.style.overflow = 'hidden';
    clone.style.backgroundColor = '#000';
    
    const cloneImg = document.createElement('img');
    cloneImg.src = imgSrc;
    cloneImg.style.width = '100%';
    cloneImg.style.height = '100%';
    cloneImg.style.objectFit = 'cover';
    cloneImg.style.display = 'block';
    
    clone.appendChild(cloneImg);
    document.body.appendChild(clone);

    // C. FREEZE THE BACKGROUND
    // Prevent scrolling during transition
    document.body.style.overflow = 'hidden';
    
    // D. UPDATE CONTENT
    updateProjectContent(projectInfo);

    // E. GSAP TIMELINE (Play)
    const tl = gsap.timeline({
        onComplete: () => {
            // Cleanup after animation
            clone.remove();
            isAnimating = false;
        }
    });

    // Step 1: Fade out the horizontal strip
    tl.to('.horizontal-strip', { 
        duration: 0.5, 
        opacity: 0, 
        ease: 'power2.out' 
    })

    // Step 2: Animate the Clone to Fullscreen Hero Position (Last)
    .to(clone, {
        top: 0,
        left: 0,
        width: '100%',
        height: '60vh', // Match CSS .hero-image-container height
        duration: 1.2,
        ease: 'expo.inOut' // Exponential ease for luxury effect
    }, '-=0.5') // Overlap with previous animation

    // Step 3: Reveal the Detail View Container
    .add(() => {
        // Ensure CSS .active rules apply (makes display:block)
        if (detailView.classList) detailView.classList.add('active');
        detailView.style.visibility = 'visible';
        detailView.style.opacity = '1';
        
        // Inject the image into the static container
        const staticImg = document.createElement('img');
        staticImg.src = imgSrc;
        heroContainer.innerHTML = '';
        heroContainer.appendChild(staticImg);
    })

    // Step 4: Animate Text Content Up
    .to(detailContent, {
        opacity: 1,
        y: 0, // Slide up to natural position
        duration: 0.8,
        ease: 'power3.out'
    }, '-=0.4'); // Slight overlap for smoothness
}

// --- UPDATE PROJECT CONTENT ---
function updateProjectContent(projectInfo) {
    // Update metadata
    const metaYear = detailContent.querySelector('.meta-year');
    const metaRole = detailContent.querySelector('.meta-role');
    const metaClient = detailContent.querySelector('.meta-client');
    
    if (metaYear) metaYear.textContent = `Year: ${projectInfo.year}`;
    if (metaRole) metaRole.textContent = `Role: ${projectInfo.role}`;
    if (metaClient) metaClient.textContent = `Client: ${projectInfo.client}`;
    
    // Update title
    const heroTitle = detailContent.querySelector('.hero-title');
    if (heroTitle) {
        if (projectInfo.titleZh) {
            heroTitle.innerHTML = `${projectInfo.title}<br>${projectInfo.titleZh}`;
        } else {
            heroTitle.textContent = projectInfo.title;
        }
    }
    
    // Update description
    const leadParagraph = detailContent.querySelector('.lead-paragraph');
    if (leadParagraph) {
        leadParagraph.textContent = projectInfo.description;
    }
    
    // Update extended text
    const bodyParagraph = detailContent.querySelector('.body-paragraph');
    if (bodyParagraph) {
        bodyParagraph.textContent = projectInfo.extended;
    }
}

// --- CLOSING LOGIC ---
function closeProject() {
    if (isAnimating) return;
    
    isAnimating = true;
    
    const tl = gsap.timeline({
        onComplete: () => {
            detailView.style.visibility = 'hidden';
            detailView.style.opacity = '0';
            if (detailView.classList) detailView.classList.remove('active');
            heroContainer.innerHTML = ''; // Clean DOM
            
            // Reset content opacity and position
            gsap.set(detailContent, { opacity: 0, y: 50 });
            
            // Restore scrolling
            document.body.style.overflow = '';
            
            isAnimating = false;
            currentProjectData = null;
        }
    });

    // Reverse animation sequence
    tl.to(detailContent, { 
        opacity: 0, 
        y: 50, 
        duration: 0.5,
        ease: 'power2.in'
    })
    .to(detailView, { 
        opacity: 0, 
        duration: 0.5,
        ease: 'power2.in'
    }, '-=0.2')
    .to('.horizontal-strip', { 
        opacity: 1, 
        duration: 0.5,
        ease: 'power2.out'
    }, '-=0.3')
    .add(() => {
        // Show header again
        const header = document.querySelector('header');
        if (header) header.style.display = '';
    });
}

// --- INITIALIZE ON LOAD ---
initFlipAnimation();

// --- EXPOSE closeProject TO GLOBAL SCOPE ---
// Required for onclick handler in HTML
window.closeProject = closeProject;
