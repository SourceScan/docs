const link = document.querySelector("#replacement");
const anchors = JSON.parse(link.dataset.anchors);
let fragment = window.location.hash.slice(1);
try {
  fragment = decodeURIComponent(fragment);
} catch {
  // Malformed fragments fall back to the page's replacement.
}
const destination = Object.hasOwn(anchors, fragment) ? anchors[fragment] : link.href;
window.location.replace(destination);
