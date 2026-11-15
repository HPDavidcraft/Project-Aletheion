document.querySelectorAll('[data-scroll-to]').forEach(button => {
  button.addEventListener('click', () => {
    const target = document.getElementById(button.dataset.scrollTo);
    if (!target) throw new Error(`Missing scroll target: ${button.dataset.scrollTo}`);
    target.scrollIntoView({ behavior: 'smooth' });
  });
});
