const STAGE_W = 1280;
const STAGE_H = 720;
const SVG_NS = "http://www.w3.org/2000/svg";
const STEP_MS = 80;
const BASE_MS = 120;

const stage = document.querySelector(".stage");
const slides = [...document.querySelectorAll(".slide")];
const progress = document.querySelector(".progress");
const counter = document.querySelector(".counter");
const announcer = document.querySelector(".announcer");
let current = 0;

function fit() {
  const scale = Math.min(innerWidth / STAGE_W, innerHeight / STAGE_H);
  stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
}

// offsetLeft/Top ignore CSS transforms, so positions stay right while nodes animate and the stage is scaled.
function boxIn(el, container) {
  let x = 0;
  let y = 0;
  let node = el;
  while (node && node !== container) {
    x += node.offsetLeft;
    y += node.offsetTop;
    node = node.offsetParent;
  }
  return { x, y, w: el.offsetWidth, h: el.offsetHeight };
}

const NORMALS = { t: [0, -1], r: [1, 0], b: [0, 1], l: [-1, 0] };

function port(box, side, f = 0.5) {
  const { x, y, w, h } = box;
  return {
    t: [x + w * f, y],
    r: [x + w, y + h * f],
    b: [x + w * f, y + h],
    l: [x, y + h * f],
  }[side];
}

// Edges sharing a side are spread along it, ordered by where their other end sits, so fans don't cross.
function spreadPorts(edges) {
  const groups = new Map();
  for (const edge of edges) {
    for (const [end, other] of [["from", "to"], ["to", "from"]]) {
      const key = `${edge[end].id}:${edge[end].side}`;
      const vertical = edge[end].side === "l" || edge[end].side === "r";
      const box = edge[other].box;
      const sortKey = vertical ? box.y + box.h / 2 : box.x + box.w / 2;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push({ end: edge[end], sortKey });
    }
  }
  for (const members of groups.values()) {
    members.sort((a, b) => a.sortKey - b.sortKey);
    members.forEach((m, i) => {
      m.end.f = members.length === 1 ? 0.5 : 0.15 + (0.7 * (i + 0.5)) / members.length;
    });
  }
}

function autoSides(a, b) {
  if (b.x >= a.x + a.w) {
    return ["r", "l"];
  }
  if (a.x >= b.x + b.w) {
    return ["l", "r"];
  }
  if (b.y >= a.y + a.h) {
    return ["b", "t"];
  }
  return ["t", "b"];
}

// Between parallel sides the reach is capped at half the gap; a longer one overshoots and the curves of a fan cross.
function controlReach(p1, p2, n1, n2) {
  const bothVertical = n1[0] === 0 && n2[0] === 0;
  const bothHorizontal = n1[1] === 0 && n2[1] === 0;
  if (bothVertical) {
    return Math.max(20, Math.abs(p2[1] - p1[1]) * 0.5);
  }
  if (bothHorizontal) {
    return Math.max(20, Math.abs(p2[0] - p1[0]) * 0.5);
  }
  return Math.max(28, Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) * 0.42);
}

const EDGE =/^\s*([\w-]+)(?:\.([trbl]))?\s*([>~])\s*([\w-]+)(?:\.([trbl]))?\s*(?::(.*))?$/;

function drawDiagram(dia) {
  dia.querySelectorAll(":scope > .wires, :scope > .wlabel, :scope > .sr-only").forEach((el) => el.remove());

  const nodes = [...dia.querySelectorAll("[data-id]")];
  const order = new Map(nodes.map((el, i) => [el.dataset.id, i]));
  nodes.forEach((el, i) => el.style.setProperty("--i", i));

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.classList.add("wires");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("width", dia.offsetWidth);
  svg.setAttribute("height", dia.offsetHeight);
  dia.prepend(svg);

  const edges = [];
  for (const spec of (dia.dataset.edges || "").split(";")) {
    const match = spec.match(EDGE);
    if (!match) {
      continue;
    }
    const [, fromId, fromSide, kind, toId, toSide, label] = match;
    const fromEl = dia.querySelector(`[data-id="${fromId}"]`);
    const toEl = dia.querySelector(`[data-id="${toId}"]`);
    if (!fromEl || !toEl) {
      console.warn("edge with unknown node:", spec);
      continue;
    }
    const a = boxIn(fromEl, dia);
    const b = boxIn(toEl, dia);
    const [sa, sb] = autoSides(a, b);
    edges.push({
      from: { id: fromId, box: a, side: fromSide || sa },
      to: { id: toId, box: b, side: toSide || sb },
      dashed: kind === "~",
      label,
    });
  }
  spreadPorts(edges);

  for (const { from, to, dashed, label } of edges) {
    const p1 = port(from.box, from.side, from.f);
    const p2 = port(to.box, to.side, to.f);
    const n1 = NORMALS[from.side];
    const n2 = NORMALS[to.side];
    const k = controlReach(p1, p2, n1, n2);
    const c1 = [p1[0] + n1[0] * k, p1[1] + n1[1] * k];
    const c2 = [p2[0] + n2[0] * k, p2[1] + n2[1] * k];
    const delay = Math.max(order.get(from.id), order.get(to.id)) * STEP_MS + BASE_MS + 180;

    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", `M${p1} C${c1} ${c2} ${p2}`);
    path.setAttribute("pathLength", "1");
    path.classList.add(dashed ? "dash" : "flow");
    path.style.animationDelay = `${delay}ms`;
    svg.append(path);

    const back = [p2[0] + n2[0] * 9, p2[1] + n2[1] * 9];
    const perp = [-n2[1] * 5, n2[0] * 5];
    const head = document.createElementNS(SVG_NS, "polygon");
    head.setAttribute("points", `${p2} ${back[0] + perp[0]},${back[1] + perp[1]} ${back[0] - perp[0]},${back[1] - perp[1]}`);
    head.style.animationDelay = `${delay + 380}ms`;
    svg.append(head);

    if (label) {
      const mid = [0, 1].map((i) => (p1[i] + 3 * c1[i] + 3 * c2[i] + p2[i]) / 8);
      const tag = document.createElement("span");
      tag.className = "wlabel";
      tag.setAttribute("aria-hidden", "true");
      tag.textContent = label.trim();
      tag.style.left = `${mid[0]}px`;
      tag.style.top = `${mid[1]}px`;
      tag.style.animationDelay = `${delay + 250}ms`;
      dia.append(tag);
    }
  }

  dia.append(describeEdges(dia, edges));
}

function nodeName(dia, id) {
  const el = dia.querySelector(`[data-id="${id}"]`);
  return (el.querySelector("b") || el).textContent.trim();
}

// The wires are aria-hidden SVG, so screen readers get the flow from this list instead.
function describeEdges(dia, edges) {
  const box = document.createElement("div");
  box.className = "sr-only";
  const intro = document.createElement("p");
  intro.textContent = "Conexiones del diagrama:";
  const list = document.createElement("ul");
  for (const { from, to, label } of edges) {
    const item = document.createElement("li");
    const via = label ? ` (${label.trim()})` : "";
    item.textContent = `${nodeName(dia, from.id)} lleva a ${nodeName(dia, to.id)}${via}.`;
    list.append(item);
  }
  box.append(intro, list);
  return box;
}

function staggerBlocks(slide) {
  const groups = slide.querySelectorAll(".tiles, .families, .chips, .stagger");
  groups.forEach((group) => {
    [...group.children].forEach((child, i) => child.style.setProperty("--i", i + 2));
  });
}

function drawAll() {
  document.querySelectorAll(".dia").forEach(drawDiagram);
}

function labelSlides() {
  slides.forEach((slide, i) => {
    slide.setAttribute("role", "group");
    slide.setAttribute("aria-roledescription", "diapositiva");
    slide.setAttribute("aria-label", `${i + 1} de ${slides.length}`);
  });
  document.querySelectorAll(".n.hitl").forEach((node) => {
    const note = document.createElement("span");
    note.className = "sr-only";
    note.textContent = " Puede parar a preguntar.";
    node.append(note);
  });
}

function slideTitle(slide) {
  return (slide.querySelector("h1, h2, .quote") || slide).textContent.trim();
}

function buildProgress() {
  slides.forEach((slide, i) => {
    const seg = document.createElement("i");
    seg.title = `${i + 1}`;
    seg.addEventListener("click", () => go(i));
    progress.append(seg);
    staggerBlocks(slide);
  });
}

function go(index, announce = true) {
  current = Math.max(0, Math.min(slides.length - 1, index));
  slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
  [...progress.children].forEach((seg, i) => {
    seg.classList.toggle("on", i === current);
    seg.classList.toggle("done", i < current);
  });
  stage.className = `stage ${[...slides[current].classList].find((c) => c.startsWith("fam-")) || ""}`;
  counter.textContent = `${current + 1} / ${slides.length}`;
  history.replaceState(null, "", `#${current + 1}`);
  if (announce) {
    announcer.textContent = `Diapositiva ${current + 1} de ${slides.length}: ${slideTitle(slides[current])}`;
  }
}

function onKey(event) {
  // A focused button or link already acts on Enter/Space; handling it here too would skip a slide.
  if (event.target.closest("button, a") && (event.key === "Enter" || event.key === " ")) {
    return;
  }
  const next = ["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"];
  const prev = ["ArrowLeft", "ArrowUp", "PageUp", "Backspace"];
  if (next.includes(event.key)) {
    event.preventDefault();
    go(current + 1);
  } else if (prev.includes(event.key)) {
    event.preventDefault();
    go(current - 1);
  } else if (event.key === "Home") {
    go(0);
  } else if (event.key === "End") {
    go(slides.length - 1);
  } else if (event.key === "f") {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen();
    }
  }
}

let touchX = null;
addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
addEventListener("touchend", (e) => {
  if (touchX === null) {
    return;
  }
  const dx = e.changedTouches[0].clientX - touchX;
  if (Math.abs(dx) > 50) {
    go(current + (dx < 0 ? 1 : -1));
  }
  touchX = null;
});

document.querySelector("[data-prev]").addEventListener("click", () => go(current - 1));
document.querySelector("[data-next]").addEventListener("click", () => go(current + 1));
addEventListener("keydown", onKey);
addEventListener("resize", fit);

labelSlides();
buildProgress();
fit();
function slideFromHash() {
  const key = decodeURIComponent(location.hash.slice(1));
  const named = slides.findIndex((slide) => slide.id === key);
  if (named !== -1) {
    return named;
  }
  return (parseInt(key, 10) || 1) - 1;
}

addEventListener("hashchange", () => go(slideFromHash()));
go(slideFromHash(), false);
drawAll();
document.fonts.ready.then(drawAll);
