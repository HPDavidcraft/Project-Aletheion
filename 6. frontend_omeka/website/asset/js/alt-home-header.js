(() => {
  const form = document.getElementById('quick-search-form');
  const input = document.getElementById('quick-search');
  const status = document.querySelector('.site-header__status');

  form?.addEventListener('submit', event => {
    event.preventDefault();
    const query = input?.value.trim().toLocaleLowerCase();
    if (!query || !status) return;

    document.querySelectorAll('[data-search-match="true"]').forEach(element => {
      element.removeAttribute('data-search-match');
    });

    const candidates = document.querySelectorAll(
      '#hero h1, #hero .tagline, .demo-banner, .about-content h2, .about-content p, .evidence-gallery-intro h2, .film-card, .timeline-item h3'
    );
    const match = Array.from(candidates).find(element =>
      element.textContent.toLocaleLowerCase().includes(query)
    );

    if (match) {
      match.setAttribute('data-search-match', 'true');
      match.scrollIntoView({ behavior: 'smooth', block: 'center' });
      status.textContent = 'Match found on this demo page.';
    } else {
      status.textContent = 'No match found on this demo page.';
    }
  });

  document.querySelectorAll('[data-demo-control]').forEach(button => {
    button.addEventListener('click', () => {
      if (!status) return;
      status.textContent = button.dataset.demoControl === 'language'
        ? 'Language selection is a demo placeholder; English is currently available.'
        : 'Sign-in is a demo placeholder; no account service is connected.';
    });
  });
})();
