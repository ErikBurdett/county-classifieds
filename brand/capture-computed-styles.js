/**
 * Run in the browser DevTools console on an authorized TheCountyPost page.
 * Adapt SELECTORS to the real DOM first. The script copies a JSON snapshot.
 * It reads computed presentation values only; it does not download assets.
 */
(() => {
  const SELECTORS = {
    body: "body",
    masthead: "header",
    primaryNavigation: "nav",
    heading1: "h1",
    heading2: "h2",
    bodyCopy: "main p",
    primaryLink: "main a",
    primaryButton: "button, [class*='button'], [class*='btn']",
    formInput: "input:not([type='hidden']), select, textarea",
    card: "article, [class*='card']",
    footer: "footer",
  };

  const PROPERTIES = [
    "display", "color", "backgroundColor", "fontFamily", "fontSize",
    "fontWeight", "fontStyle", "lineHeight", "letterSpacing",
    "textTransform", "textDecorationLine", "maxWidth", "width",
    "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "marginTop", "marginRight", "marginBottom", "marginLeft",
    "borderTopWidth", "borderTopStyle", "borderTopColor", "borderRadius",
    "boxShadow", "gap", "columnGap", "rowGap"
  ];

  const snapshot = {
    url: location.href,
    title: document.title,
    capturedAt: new Date().toISOString(),
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio,
    },
    selectors: {},
  };

  for (const [name, selector] of Object.entries(SELECTORS)) {
    const element = document.querySelector(selector);
    if (!element) {
      snapshot.selectors[name] = { selector, found: false };
      continue;
    }
    const styles = getComputedStyle(element);
    const values = {};
    for (const property of PROPERTIES) values[property] = styles[property];
    snapshot.selectors[name] = {
      selector,
      found: true,
      tagName: element.tagName,
      classes: [...element.classList],
      values,
    };
  }

  const json = JSON.stringify(snapshot, null, 2);
  console.log(json);
  if (typeof copy === "function") copy(json);
  return snapshot;
})();
