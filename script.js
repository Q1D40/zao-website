(() => {
  const scene = document.querySelector(".scene");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

  if (!scene) return;

  let frame = 0;
  let lightX = 0;
  let lightY = 0;

  const paint = () => {
    scene.style.setProperty("--light-x", `${lightX.toFixed(2)}px`);
    scene.style.setProperty("--light-y", `${lightY.toFixed(2)}px`);
    scene.style.setProperty("--surface-x", `${(lightX * 0.2).toFixed(2)}px`);
    scene.style.setProperty("--surface-y", `${(lightY * 0.2).toFixed(2)}px`);
    frame = 0;
  };

  const reset = () => {
    if (frame) window.cancelAnimationFrame(frame);
    frame = 0;
    for (const property of ["--light-x", "--light-y", "--surface-x", "--surface-y"]) {
      scene.style.removeProperty(property);
    }
  };

  const followLight = (event) => {
    if (reducedMotion.matches || !finePointer.matches) return;

    lightX = (event.clientX / window.innerWidth - 0.5) * 28;
    lightY = (event.clientY / window.innerHeight - 0.5) * 20;
    if (!frame) frame = window.requestAnimationFrame(paint);
  };

  window.addEventListener("pointermove", followLight, { passive: true });
  document.addEventListener("pointerleave", reset, { passive: true });
  window.addEventListener("blur", reset);
  reducedMotion.addEventListener("change", reset);
  finePointer.addEventListener("change", reset);
  document.addEventListener("visibilitychange", () => {
    scene.classList.toggle("is-paused", document.hidden);
    if (document.hidden) reset();
  });
})();
