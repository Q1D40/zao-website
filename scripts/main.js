(() => {
  const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (preference.matches || typeof Element.prototype.animate !== "function") return;
  const animations = [];
  const enter = (selector, keyframes, delay = 0) => {
    const element = document.querySelector(selector);
    if (!element) return;
    const animation = element.animate(keyframes, {
      duration: 550, delay, easing: "cubic-bezier(.16, 1, .3, 1)", fill: "backwards",
    });
    animations.push(animation);
    animation.finished.then(() => animation.cancel()).catch(() => {});
  };
  const rise = [{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "none" }];
  enter('[data-enter="identity"]', rise);
  enter('[data-enter="copy"]', rise, 75);
  enter('[data-enter="art"]', [{ opacity: 0 }, { opacity: 1 }]);
  const stop = () => animations.forEach((animation) => animation.cancel());
  preference.addEventListener("change", (event) => { if (event.matches) stop(); });
  window.addEventListener("pagehide", stop, { once: true });
})();
