import { onMounted, onUnmounted } from "vue";

/** Delegate pointer tracking to cards without per-frame Vue renders. */
export function useSpotlight() {
  let active: HTMLElement | null = null;
  let frame = 0;
  let x = 0;
  let y = 0;
  let media: MediaQueryList;
  function reset() {
    active?.removeAttribute("data-lit");
    active = null;
    cancelAnimationFrame(frame);
    frame = 0;
  }
  function move(event: PointerEvent) {
    if (!media.matches || event.pointerType === "touch") return;
    const card = (event.target as Element).closest<HTMLElement>(
      ".feature, .release-manifest",
    );
    if (active !== card) {
      reset();
      active = card;
    }
    if (!card) return;
    x = event.clientX;
    y = event.clientY;
    if (!frame)
      frame = requestAnimationFrame(() => {
        if (active) {
          const rect = active.getBoundingClientRect();
          active.style.setProperty("--pointer-x", `${x - rect.left}px`);
          active.style.setProperty("--pointer-y", `${y - rect.top}px`);
          active.setAttribute("data-lit", "");
        }
        frame = 0;
      });
  }
  onMounted(() => {
    media = matchMedia(
      "(hover: hover) and (prefers-reduced-motion: no-preference)",
    );
    document.addEventListener("pointermove", move, { passive: true });
    document.addEventListener("pointerleave", reset);
    media.addEventListener("change", reset);
  });
  onUnmounted(() => {
    reset();
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerleave", reset);
    media.removeEventListener("change", reset);
  });
}
