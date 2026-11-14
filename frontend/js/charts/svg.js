// SVG element helpers shared by the charts.
const SVG = "http://www.w3.org/2000/svg";

export function svg(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  children.flat(Infinity).forEach((c) => c && node.append(c));
  return node;
}

export function text(x, y, value, attrs = {}) {
  const node = svg("text", { x, y, ...attrs });
  node.textContent = value;
  return node;
}
