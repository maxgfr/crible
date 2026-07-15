import "@testing-library/jest-dom/vitest";

// jsdom has no layout — the drawer's jump buttons call scrollIntoView
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
