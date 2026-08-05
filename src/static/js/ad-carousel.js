(() => {
  "use strict";

  document.querySelectorAll("[data-ad-carousel]").forEach((carousel) => {
    const track = carousel.querySelector("[data-ad-track]");
    const items = [...carousel.querySelectorAll(".ad-slot__creative")];
    if (!(track instanceof HTMLElement) || items.length < 2) return;

    const move = (direction) => {
      const center = track.scrollLeft + track.clientWidth / 2;
      const current = items.reduce(
        (closest, item, index) => {
          const distance = Math.abs(item.offsetLeft + item.offsetWidth / 2 - center);
          return distance < closest.distance ? { index, distance } : closest;
        },
        { index: 0, distance: Number.POSITIVE_INFINITY },
      ).index;
      const next = (current + direction + items.length) % items.length;
      track.scrollTo({
        left: items[next].offsetLeft + items[next].offsetWidth / 2 - track.clientWidth / 2,
        behavior: "smooth",
      });
    };

    carousel.querySelector("[data-ad-previous]")?.addEventListener("click", () => move(-1));
    carousel.querySelector("[data-ad-next]")?.addEventListener("click", () => move(1));

    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      window.setInterval(() => move(1), 20_000);
    }
  });
})();
