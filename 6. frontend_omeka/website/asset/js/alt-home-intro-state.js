(() => {
  const introKey = 'pleroma-alt-home-intro-shown';
  if (sessionStorage.getItem(introKey)) {
    document.documentElement.classList.add('skip-intro');
    return;
  }
  sessionStorage.setItem(introKey, 'true');
})();
