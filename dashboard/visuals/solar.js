/* The 3D solar system shown under the tutor's answer when a question is about the Sun, the planets,
   their moons or orbits. The backend picks the view (backend/app/services/visuals.py):
     overview  the whole system turning           planet   a close-up with its moons and facts
     compare   chosen bodies side by side, true sizes   sizes   every planet at its true size
     orbits    the orbits from above, real relative speeds
   app.js dispatches "mentora:visual" { type: "mount", element, visual }; this file draws into the element.
   Only the newest answer's view is live (one 3D context); older ones keep a still picture.
   Facts: NASA planetary fact sheet. Surfaces are generated here (no image files).
   Decoration on top of the answer: if anything fails here, the chat works as before. */

import * as THREE from "three";

/* ---------- its own styles, delivered with this file: a browser can keep an old styles.css after
   an update, and the view must never depend on it (that broke it once) ---------- */

const STYLES = `
.visual-slot { margin: .9rem 0 0 1rem; max-width: 68ch; }
.visual {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #2f3d5c;
  background: #05040c;
  color: #e3e8ff;
  font-family: var(--sans);
}
.visual .stage { position: relative; aspect-ratio: 16 / 10; }
.visual .stage canvas, .visual .stage .still { display: block; width: 100%; height: 100%; object-fit: cover; touch-action: none; cursor: grab; }
.visual .labels { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.visual .labels span {
  position: absolute; left: 0; top: 0; padding-top: 2px;
  font-size: .72rem; color: #b8c4ea; white-space: nowrap; text-shadow: 0 0 4px #000, 0 0 2px #000;
}
.visual .labels span.on { color: #fff; font-weight: 700; font-size: .8rem; }
.visual .facts {
  position: absolute; top: .55rem; right: .55rem; width: min(17rem, 46%); max-height: calc(100% - 3.6rem); overflow: auto;
  padding: .6rem .75rem; border-radius: 10px; background: rgba(10, 10, 28, .82); backdrop-filter: blur(4px);
  font-size: .78rem; line-height: 1.4;
}
.visual .facts h4 { margin: 0 0 .15rem; font: 600 1rem var(--serif); color: #fff; }
.visual .facts .kind { margin: 0 0 .35rem; color: #9fd4ff; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; }
.visual .facts .note { margin: 0 0 .45rem; color: #cfd6f5; }
.visual .facts dl { display: grid; grid-template-columns: auto 1fr; gap: .15rem .6rem; margin: 0; }
.visual .facts dt { color: #8f9cc6; }
.visual .facts dd { margin: 0; color: #fff; }
.visual .facts table { width: 100%; border-collapse: collapse; font-size: .74rem; }
.visual .facts th, .visual .facts td { padding: .2rem .3rem .2rem 0; border-bottom: 1px solid rgba(255,255,255,.08); text-align: left; vertical-align: top; }
.visual .facts tr th:first-child { color: #8f9cc6; font-weight: 400; }
.visual .facts .source { margin: .45rem 0 0; color: #7480a8; font-size: .68rem; }
.visual .tools { position: absolute; left: .55rem; bottom: .55rem; display: flex; flex-wrap: wrap; gap: .35rem; }
.visual .tools button {
  padding: .3rem .65rem; border-radius: 99px; border: 1px solid #3a4a72; background: rgba(10, 10, 28, .75);
  color: #dfe6ff; font-size: .75rem; cursor: pointer;
}
.visual .tools button[aria-pressed="true"] { background: #2b4a86; border-color: #5b86d6; color: #fff; }
.visual .hint { position: absolute; right: .7rem; bottom: .5rem; margin: 0; font-size: .68rem; color: #6f7aa3; }
.visual.frozen .facts, .visual.frozen .hint { display: none; }
.visual.asleep { padding: .6rem; }
.visual .again { padding: .45rem .8rem; border-radius: 99px; border: 1px solid #3a4a72; background: #121a33; color: #dfe6ff; cursor: pointer; font-size: .8rem; }
.visual.frozen:not(.asleep) .tools { left: 50%; bottom: 50%; transform: translate(-50%, 50%); }

@media (max-width: 600px) { /* facts go under the picture instead of over it */
  .visual-slot { margin-left: 0; }
  .visual .facts { position: static; width: auto; max-height: none; border-radius: 0; }
  .visual .hint { display: none; }
}
`;

if (!document.getElementById("solar-styles")) {
  const style = document.createElement("style");
  style.id = "solar-styles";
  style.textContent = STYLES;
  document.head.append(style);
}

/* ---------- facts (NASA planetary fact sheet; moon counts change as new ones are found) ---------- */

const FACTS = {
  sun: { name: "Sun", kind: "Star", diameter: 1392700, temp: 5500, tempNote: "surface", gravity: 274,
    note: "A star: a huge ball of hydrogen and helium holding 99.8% of all the mass in the solar system." },
  mercury: { name: "Mercury", kind: "Planet", diameter: 4879, distance: 57.9, year: 88.0, day: 4222.6, moons: "0", temp: 167, gravity: 3.7, tilt: 0.03,
    note: "The smallest planet and the closest to the Sun. With almost no air, it is scorching by day and freezing at night." },
  venus: { name: "Venus", kind: "Planet", diameter: 12104, distance: 108.2, year: 224.7, day: 2802.0, moons: "0", temp: 464, gravity: 8.9, tilt: 177.4,
    note: "The hottest planet: thick carbon-dioxide clouds trap the heat. It spins backwards, very slowly." },
  earth: { name: "Earth", kind: "Planet", diameter: 12756, distance: 149.6, year: 365.2, day: 24.0, moons: "1", temp: 15, gravity: 9.8, tilt: 23.4,
    note: "The only world known to have life, with liquid water covering about 71% of its surface." },
  mars: { name: "Mars", kind: "Planet", diameter: 6792, distance: 228.0, year: 687.0, day: 24.7, moons: "2", temp: -65, gravity: 3.7, tilt: 25.2,
    note: "The red planet: its dust is rich in iron oxide (rust). It has Olympus Mons, the tallest volcano known." },
  jupiter: { name: "Jupiter", kind: "Planet", diameter: 142984, distance: 778.5, year: 4331, day: 9.9, moons: "95+", temp: -110, gravity: 23.1, tilt: 3.1,
    note: "The largest planet, a gas giant. Its Great Red Spot is a storm wider than Earth." },
  saturn: { name: "Saturn", kind: "Planet", diameter: 120536, distance: 1432.0, year: 10747, day: 10.7, moons: "270+", temp: -140, gravity: 9.0, tilt: 26.7,
    note: "A gas giant with bright rings of ice and rock. It is less dense than water." },
  uranus: { name: "Uranus", kind: "Planet", diameter: 51118, distance: 2867.0, year: 30589, day: 17.2, moons: "28+", temp: -195, gravity: 8.7, tilt: 97.8,
    note: "An ice giant that rolls around the Sun on its side, tilted about 98 degrees." },
  neptune: { name: "Neptune", kind: "Planet", diameter: 49528, distance: 4515.0, year: 59800, day: 16.1, moons: "16", temp: -200, gravity: 11.0, tilt: 28.3,
    note: "The farthest planet, an ice giant with the fastest winds in the solar system." },
  pluto: { name: "Pluto", kind: "Dwarf planet", diameter: 2376, distance: 5906.4, year: 90560, day: 153.3, moons: "5", temp: -225, gravity: 0.7, tilt: 119.5,
    note: "A dwarf planet since 2006, out in the icy Kuiper Belt beyond Neptune." },
  moon: { name: "Moon", kind: "Earth's moon", diameter: 3475, fromEarth: 0.384, year: 27.3, day: 708.7, temp: -20, gravity: 1.6, tilt: 6.7,
    note: "Earth's only natural satellite. The same side always faces us; its phases are how much of its lit half we see." },
};
const PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"];
const ORBITING = [...PLANETS, "pluto"];
const EARTH = FACTS.earth;

// Names as they may be spoken (English, Malayalam stems), to light up the planet being talked about.
const SPOKEN = {
  sun: ["sun", "സൂര്യ"], mercury: ["mercury", "ബുധ"], venus: ["venus", "ശുക്ര"], earth: ["earth", "ഭൂമി"],
  mars: ["mars", "ചൊവ്വ"], jupiter: ["jupiter", "വ്യാഴ"], saturn: ["saturn", "ശനി"], uranus: ["uranus", "യുറാനസ"],
  neptune: ["neptune", "നെപ്റ്റ്യൂൺ"], pluto: ["pluto", "പ്ലൂട്ടോ"], moon: ["moon", "ചന്ദ്ര"],
};

// The biggest moons, so close-ups look right: [name, size vs the planet, orbit in planet radii (squeezed)].
const MOONS = {
  earth: [["Moon", 0.27, 3.2]],
  mars: [["Phobos", 0.05, 2.0], ["Deimos", 0.035, 2.8]],
  jupiter: [["Io", 0.07, 1.8], ["Europa", 0.06, 2.3], ["Ganymede", 0.09, 2.9], ["Callisto", 0.085, 3.6]],
  saturn: [["Titan", 0.1, 3.4], ["Rhea", 0.04, 2.7]],
  uranus: [["Titania", 0.07, 2.4], ["Oberon", 0.065, 3.0]],
  neptune: [["Triton", 0.11, 2.6]],
  pluto: [["Charon", 0.51, 2.6]],
};

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const fmt = (n, digits = 0) => n.toLocaleString("en-IN", { maximumFractionDigits: digits });

/* ---------- surfaces, drawn with noise instead of downloaded pictures ---------- */

function rng(seed) { // mulberry32
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Smooth noise sampled on the sphere itself (3D), so surfaces have no seams or stretched poles.
function hash3(x, y, z, seed) {
  let h = Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(z, 1274126177) ^ Math.imul(seed, 1597334677);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

function noise3(x, y, z, seed) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
  const s = (t) => t * t * (3 - 2 * t);
  const sx = s(x - xi), sy = s(y - yi), sz = s(z - zi);
  const c = (dx, dy, dz) => hash3(xi + dx, yi + dy, zi + dz, seed);
  const lerp = (a, b, t) => a + (b - a) * t;
  return lerp(
    lerp(lerp(c(0, 0, 0), c(1, 0, 0), sx), lerp(c(0, 1, 0), c(1, 1, 0), sx), sy),
    lerp(lerp(c(0, 0, 1), c(1, 0, 1), sx), lerp(c(0, 1, 1), c(1, 1, 1), sx), sy), sz);
}

function fbm3(x, y, z, seed, octaves) {
  let sum = 0, amp = 0.5, freq = 1, norm = 0;
  for (let i = 0; i < octaves; i += 1) {
    sum += amp * noise3(x * freq, y * freq, z * freq, seed + i * 17);
    norm += amp; amp *= 0.5; freq *= 2;
  }
  return sum / norm;
}

const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * clamp(t, 0, 1));

// Each paints one pixel: u, v across the map (v = 0 at the north pole), N(freq, octaves, salt) = noise there.
const SURFACES = {
  sun: (u, v, N) => mix([255, 120, 20], [255, 225, 120], N(4, 5) * 1.6 - 0.3),
  mercury: (u, v, N) => mix([95, 90, 88], [190, 182, 175], N(4, 5) * 1.4 - 0.25 + (N(14, 2, 9) > 0.66 ? 0.3 : 0)),
  venus: (u, v, N) => mix([200, 150, 80], [245, 220, 165], N(2.5, 5) * 1.5 - 0.2),
  earth: (u, v, N) => {
    if (Math.abs(v - 0.5) * 2 > 0.86) return [240, 245, 250];
    const land = N(2.2, 5);
    let c = land > 0.54 ? mix([70, 120, 55], [155, 135, 90], N(6, 4, 3) * 1.6 - 0.3) : mix([15, 45, 110], [40, 95, 170], land * 1.6 - 0.3);
    const cloud = N(3.5, 4, 7);
    if (cloud > 0.58) c = mix(c, [255, 255, 255], (cloud - 0.58) * 4);
    return c;
  },
  mars: (u, v, N) => (Math.abs(v - 0.5) * 2 > 0.9 ? [235, 225, 215] : mix([110, 45, 25], [205, 105, 60], N(3, 5) * 1.6 - 0.3)),
  jupiter: (u, v, N) => {
    const spot = ((u - 0.65) / 0.06) ** 2 + ((v - 0.66) / 0.035) ** 2;
    if (spot < 1) return mix([170, 70, 45], [205, 120, 85], spot);
    return mix([150, 105, 70], [235, 215, 180], Math.sin(v * Math.PI * 14 + N(2, 4) * 5) * 0.5 + 0.5);
  },
  saturn: (u, v, N) => mix([185, 155, 100], [240, 220, 165], Math.sin(v * Math.PI * 12 + N(1.5, 3) * 3) * 0.5 + 0.5),
  uranus: (u, v, N) => mix([135, 200, 210], [180, 230, 235], N(1.5, 3) * 1.2 - 0.1),
  neptune: (u, v, N) => {
    const spot = ((u - 0.3) / 0.05) ** 2 + ((v - 0.6) / 0.03) ** 2;
    if (spot < 1) return [25, 40, 110];
    return mix([35, 70, 175], [80, 130, 225], Math.sin(v * Math.PI * 9 + N(2, 4) * 4) * 0.5 + 0.5);
  },
  pluto: (u, v, N) => {
    const heart = ((u - 0.55) / 0.12) ** 2 + ((v - 0.55) / 0.12) ** 2;
    return heart < 1 ? [235, 220, 200] : mix([120, 90, 70], [200, 170, 140], N(3, 5) * 1.6 - 0.3);
  },
  moon: (u, v, N) => mix([85, 85, 88], [195, 195, 195], N(3, 5) * 1.3 - 0.15 - (N(1.2, 3, 5) > 0.55 ? 0.3 : 0)),
  smallMoon: (u, v, N) => mix([110, 105, 100], [190, 185, 175], N(3, 4) * 1.6 - 0.3),
};

function surface(body) {
  const small = !SURFACES[body];
  const w = small ? 128 : 256, h = w / 2;
  const canvas = Object.assign(document.createElement("canvas"), { width: w, height: h });
  const ctx = canvas.getContext("2d");
  const image = ctx.createImageData(w, h);
  const seed = [...body].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7);
  const paint = SURFACES[body] || SURFACES.smallMoon;
  for (let y = 0; y < h; y += 1) {
    const lat = (0.5 - (y + 0.5) / h) * Math.PI;
    for (let x = 0; x < w; x += 1) {
      const lon = ((x + 0.5) / w) * Math.PI * 2;
      const px = Math.cos(lat) * Math.cos(lon), py = Math.sin(lat), pz = Math.cos(lat) * Math.sin(lon);
      const N = (freq, octaves, salt = 0) => fbm3(px * freq + 50, py * freq + 50, pz * freq + 50, seed + salt, octaves);
      const [r, g, b] = paint(x / w, y / h, N);
      const i = (y * w + x) * 4;
      image.data[i] = r; image.data[i + 1] = g; image.data[i + 2] = b; image.data[i + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function glowTexture(inner, outer) {
  const canvas = Object.assign(document.createElement("canvas"), { width: 128, height: 128 });
  const ctx = canvas.getContext("2d");
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, inner); g.addColorStop(0.35, outer); g.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = g; ctx.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(canvas);
}

function ringTexture() {
  const canvas = Object.assign(document.createElement("canvas"), { width: 256, height: 1 });
  const ctx = canvas.getContext("2d");
  const r = rng(5);
  for (let x = 0; x < 256; x += 1) {
    const gap = x > 150 && x < 162; // the Cassini division
    const a = gap ? 0.05 : 0.35 + 0.55 * r() * (x < 40 ? x / 40 : 1);
    ctx.fillStyle = `rgba(${215 + r() * 25},${195 + r() * 25},${150 + r() * 30},${a})`;
    ctx.fillRect(x, 0, 1, 1);
  }
  return new THREE.CanvasTexture(canvas);
}

/* ---------- scale: squeezed for the overview (or Mercury would be invisible), true for comparisons ---------- */

const overviewRadius = (b) => (b === "sun" ? 4 : 0.55 + 1.0 * (FACTS[b].diameter / EARTH.diameter) ** 0.4);
const orbitRadius = (b) => 7 + 13 * Math.sqrt(FACTS[b].distance / EARTH.distance);
const EARTH_YEAR_SECONDS = 30; // Earth goes round once in 30 s; the others keep their real ratios

/* ---------- the one live scene ---------- */

let world = null; // built on first use

function buildWorld() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "low-power", preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05040c);
  const camera = new THREE.PerspectiveCamera(42, 16 / 9, 0.01, 2000);

  const sunLight = new THREE.PointLight(0xfff2dd, 3.2, 0, 0);
  const viewLight = new THREE.DirectionalLight(0xffffff, 0);
  const ambient = new THREE.AmbientLight(0xffffff, 0.22);
  scene.add(sunLight, viewLight, viewLight.target, ambient);

  // stars
  const r = rng(11);
  const positions = new Float32Array(1800 * 3);
  for (let i = 0; i < 1800; i += 1) {
    const u = r() * 2 - 1, t = r() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    positions.set([600 * s * Math.cos(t), 600 * u, 600 * s * Math.sin(t)], i * 3);
  }
  const starGeometry = new THREE.BufferGeometry();
  starGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  scene.add(new THREE.Points(starGeometry, new THREE.PointsMaterial({ color: 0xaab4ff, size: 1.2, sizeAttenuation: false })));

  const sphere = new THREE.SphereGeometry(1, 48, 32);
  const bodies = {};
  for (const name of ["sun", ...ORBITING, "moon"]) {
    const material = name === "sun"
      ? new THREE.MeshBasicMaterial({ map: surface(name) })
      : new THREE.MeshStandardMaterial({ map: surface(name), roughness: 1, metalness: 0 });
    const mesh = new THREE.Mesh(sphere, material);
    mesh.userData.body = name;
    const holder = new THREE.Group(); // position + size; the mesh inside spins on its tilted axis
    holder.add(mesh);
    holder.rotation.z = THREE.MathUtils.degToRad(FACTS[name].tilt || 0);
    scene.add(holder);
    bodies[name] = { name, holder, mesh, angle: r() * Math.PI * 2, pos: new THREE.Vector3(), scale: 0.001, from: new THREE.Vector3(), fromScale: 0.001, blend: 1, target: 1 };
  }
  const sunGlow = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture("rgba(255,230,150,0.9)", "rgba(255,150,40,0.35)"), blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  sunGlow.scale.setScalar(4.2);
  bodies.sun.holder.add(sunGlow);
  const ring = new THREE.Mesh(new THREE.RingGeometry(1.25, 2.3, 128), new THREE.MeshBasicMaterial({
    map: ringTexture(), transparent: true, side: THREE.DoubleSide, depthWrite: false,
  }));
  const uv = ring.geometry.attributes.uv, p = ring.geometry.attributes.position;
  for (let i = 0; i < uv.count; i += 1) {
    const d = Math.hypot(p.getX(i), p.getY(i));
    uv.setXY(i, (d - 1.25) / (2.3 - 1.25), 0.5); // bands run outwards
  }
  ring.rotation.x = Math.PI / 2;
  bodies.saturn.holder.add(ring);

  // orbit paths
  const orbits = {};
  for (const name of ORBITING) {
    const points = Array.from({ length: 160 }, (_, i) => {
      const a = (i / 160) * Math.PI * 2;
      return new THREE.Vector3(Math.cos(a) * orbitRadius(name), 0, Math.sin(a) * orbitRadius(name));
    });
    const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineBasicMaterial({ color: name === "pluto" ? 0x5a5070 : 0x6a7aa8, transparent: true, opacity: 0.35 }));
    scene.add(line);
    orbits[name] = line;
  }

  // the biggest moons, shown around the planet in its close-up
  const moonMeshes = [];
  for (const [planet, list] of Object.entries(MOONS)) {
    for (const [label, size, distance] of list) {
      if (planet === "earth") continue; // Earth's Moon is a full body above
      const mesh = new THREE.Mesh(sphere, new THREE.MeshStandardMaterial({ map: surface(`${planet}-${label}`), roughness: 1 }));
      mesh.visible = false;
      scene.add(mesh);
      moonMeshes.push({ planet, label, size, distance, mesh, angle: r() * Math.PI * 2 });
    }
  }

  const glow = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture("rgba(160,210,255,0.0)", "rgba(140,200,255,0.55)"), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
  }));
  scene.add(glow);

  return {
    renderer, scene, camera, sunLight, viewLight, ambient, bodies, orbits, moonMeshes, glow, raycaster: new THREE.Raycaster(),
    card: null, view: null, cam: { pos: new THREE.Vector3(0, 80, 140), look: new THREE.Vector3(), yaw: 0, pitch: 0, zoom: 1 },
    lit: null, litUntil: 0, running: false, clock: new THREE.Clock(), shift: 0, size: null,
  };
}

/* ---------- views ---------- */

function bodiesFor(view) {
  if (view.view === "sizes") return PLANETS;
  if (view.view === "compare") return view.focus.length ? view.focus : ["earth", "mars"];
  return ["sun", ...ORBITING, "moon"];
}

// Where each body sits in a row, at true relative size, largest radius = `largest` units.
function row(names, largest) {
  const max = Math.max(...names.map((b) => FACTS[b].diameter));
  const radii = names.map((b) => Math.max((FACTS[b].diameter / max) * largest, 0.004));
  const gap = largest * 0.35;
  let x = 0;
  const xs = radii.map((rad) => { const at = x + rad; x += rad * 2 + gap; return at; });
  const width = x - gap;
  return names.map((b, i) => ({ name: b, x: xs[i] - width / 2, radius: radii[i] }));
}

function setView(view, { instant = false } = {}) {
  const W = world;
  W.view = view;
  W.instant = instant || reduceMotion;
  W.cam.yaw = 0; W.cam.pitch = 0; W.cam.zoom = 1;
  const shown = new Set(bodiesFor(view));
  const inRow = view.view === "compare" || view.view === "sizes";
  W.rowLayout = inRow ? row([...shown], view.view === "sizes" ? 2.2 : 1.6) : null;
  for (const body of Object.values(W.bodies)) {
    body.target = shown.has(body.name) ? 1 : 0;
    // glide from where it is now to its new place (then follow its orbit exactly)
    body.from = body.pos.clone();
    body.fromScale = body.scale;
    body.blend = W.instant ? 1 : 0;
  }
  if (W.card) paintCard(W.card, view);
}

function focusBody(view) {
  return view.focus.find((b) => world.bodies[b]) || null;
}

/* ---------- each frame ---------- */

function tick() {
  const W = world;
  if (!W.card || !W.card.root.isConnected) { W.running = false; return; }
  requestAnimationFrame(tick);
  if (document.hidden || !W.visible) return;
  const dt = Math.min(W.clock.getDelta(), 0.1);
  const t = W.clock.elapsedTime;
  const view = W.view;
  const ease = W.instant ? 1 : 1 - Math.exp(-dt * 2.6);
  const moving = view.view === "overview" || view.view === "orbits";
  const inRow = !!W.rowLayout;
  const focus = focusBody(view);

  // lights: the Sun lights the system; side-by-side views get an even studio light
  W.sunLight.intensity += ((inRow ? 0 : 3.2) - W.sunLight.intensity) * ease;
  W.viewLight.intensity += ((inRow ? 2.6 : 0) - W.viewLight.intensity) * ease;
  W.viewLight.position.copy(W.camera.position).add(new THREE.Vector3(-4, 6, 2));

  for (const body of Object.values(W.bodies)) {
    const facts = FACTS[body.name];
    if (body.name !== "sun" && body.name !== "moon" && moving) {
      body.angle += dt * (2 * Math.PI) / (EARTH_YEAR_SECONDS * (facts.year / EARTH.year)) * (reduceMotion ? 0.2 : 1);
    }
    let pos, scale;
    const slot = inRow && W.rowLayout.find((s) => s.name === body.name);
    if (slot) {
      pos = new THREE.Vector3(slot.x, 0, 0);
      scale = slot.radius;
    } else if (body.name === "sun") {
      pos = new THREE.Vector3(); scale = overviewRadius("sun");
    } else if (body.name === "moon") {
      const earth = W.bodies.earth;
      body.angle += dt * (moving ? 2.5 : focus === "earth" ? 0.6 : 0);
      const d = overviewRadius("earth") * 3.2;
      pos = earth.pos.clone().add(new THREE.Vector3(Math.cos(body.angle) * d, 0, Math.sin(body.angle) * d));
      scale = overviewRadius("earth") * 0.27;
    } else {
      const R = orbitRadius(body.name);
      pos = new THREE.Vector3(Math.cos(body.angle) * R, 0, Math.sin(body.angle) * R);
      scale = overviewRadius(body.name);
    }
    if (!body.target) scale *= 0.001; // not part of this view
    body.blend = Math.min(1, body.blend + dt * (W.instant ? 1000 : 0.8));
    const s = body.blend * body.blend * (3 - 2 * body.blend);
    body.pos.copy(body.from).lerp(pos, s);
    body.scale = body.fromScale + (scale - body.fromScale) * s;
    body.holder.position.copy(body.pos);
    body.holder.scale.setScalar(Math.max(body.scale, 1e-4));
    body.holder.visible = body.scale > 0.002;
    // spin: real day lengths, squeezed (Jupiter fast, Venus slowly backwards)
    const spin = body.name === "sun" ? 0.05 : clamp(24 / Math.abs(facts.day || 24), 0.02, 3) * (facts.tilt > 90 ? -1 : 1);
    body.mesh.rotation.y += dt * spin * 0.6;
  }

  for (const [name, line] of Object.entries(W.orbits)) {
    const want = inRow ? 0 : view.view === "planet" ? 0.12 : view.focus.includes(name) ? 0.95 : view.view === "orbits" ? 0.5 : 0.28;
    line.material.opacity += (want - line.material.opacity) * ease;
    line.material.color.set(view.focus.includes(name) ? 0x9fd4ff : name === "pluto" ? 0x5a5070 : 0x6a7aa8);
    line.visible = line.material.opacity > 0.02;
  }

  // moons around the planet in its close-up
  for (const moon of W.moonMeshes) {
    const show = view.view === "planet" && focus === moon.planet;
    const planet = W.bodies[moon.planet];
    moon.angle += dt * (0.9 / moon.distance);
    const d = planet.scale * moon.distance;
    moon.mesh.position.copy(planet.pos).add(new THREE.Vector3(Math.cos(moon.angle) * d, Math.sin(moon.angle * 0.7) * d * 0.05, Math.sin(moon.angle) * d));
    moon.mesh.scale.setScalar(Math.max(planet.scale * moon.size, 0.01));
    moon.mesh.visible = show;
  }

  // camera
  let look, eye;
  if (inRow) {
    const width = W.rowLayout.reduce((a, s) => Math.max(a, Math.abs(s.x) + s.radius), 0) * 2;
    const height = Math.max(...W.rowLayout.map((s) => s.radius)) * 2;
    const usable = W.camera.aspect * (view.view === "compare" && W.card.overlay ? 0.56 : 1);
    const fitW = width / (2 * Math.tan(THREE.MathUtils.degToRad(W.camera.fov / 2)) * usable);
    const fitH = height / (2 * Math.tan(THREE.MathUtils.degToRad(W.camera.fov / 2)));
    const d = Math.max(fitW, fitH) * 1.25 + 0.5;
    look = new THREE.Vector3(0, height * 0.08, 0);
    eye = new THREE.Vector3(0, d * 0.12, d);
  } else if (view.view === "planet" && focus) {
    const b = W.bodies[focus];
    const reach = focus === "sun" ? 3.6 : MOONS[focus] ? Math.max(...MOONS[focus].map((m) => m[2])) + 1.0 : 3.2;
    const up = new THREE.Vector3(0, 1, 0);
    if (focus === "moon") {
      // the Moon with Earth beside it: look between them, from the side
      const earth = W.bodies.earth.pos;
      const across = earth.clone().sub(b.pos).normalize();
      const side = new THREE.Vector3().crossVectors(up, across).normalize();
      look = b.pos.clone().lerp(earth, 0.3);
      eye = look.clone().add(side.multiplyScalar(W.bodies.earth.scale * 4.2)).add(up.clone().multiplyScalar(W.bodies.earth.scale * 1.3));
    } else {
      // from the sunlit side, a little to one side and above
      const dist = b.scale * reach * 1.4;
      const out = b.pos.lengthSq() > 1e-6 ? b.pos.clone().normalize() : new THREE.Vector3(0, 0, 1);
      const side = new THREE.Vector3().crossVectors(up, out).normalize();
      look = b.pos.clone();
      eye = look.clone().add(out.multiplyScalar(dist * 0.75)).add(side.multiplyScalar(dist * 0.6)).add(up.multiplyScalar(dist * 0.32));
    }
  } else if (view.view === "orbits") {
    const far = view.focus.length ? Math.max(...view.focus.map((b) => orbitRadius(b))) : orbitRadius("neptune");
    look = new THREE.Vector3();
    eye = new THREE.Vector3(0, far * 2.75 + 25, far * 0.3 + 5);
  } else {
    look = new THREE.Vector3();
    eye = new THREE.Vector3(0, 55, 115);
  }
  // the student's drag and zoom, around whatever the view looks at
  const offset = eye.clone().sub(look);
  offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), W.cam.yaw);
  const side = new THREE.Vector3(0, 1, 0).cross(offset).normalize();
  offset.applyAxisAngle(side, W.cam.pitch);
  eye = look.clone().add(offset.multiplyScalar(W.cam.zoom));
  W.cam.pos.lerp(eye, ease);
  W.cam.look.lerp(look, ease);
  W.camera.position.copy(W.cam.pos);
  W.camera.lookAt(W.cam.look);
  const shiftLeft = (view.view === "planet" || view.view === "compare" || view.view === "orbits") && W.card.overlay;
  W.shift += ((shiftLeft ? 0.21 : 0) - W.shift) * ease;
  if (W.size) W.camera.setViewOffset(W.size.width, W.size.height, W.size.width * W.shift, 0, W.size.width, W.size.height);

  // the body being talked about glows for a moment
  const lit = performance.now() < W.litUntil ? W.bodies[W.lit] : null;
  W.glow.visible = !!lit && lit.holder.visible;
  if (W.glow.visible) {
    W.glow.position.copy(lit.pos);
    W.glow.scale.setScalar(lit.scale * (3.2 + Math.sin(t * 5) * 0.25));
  }

  W.renderer.render(W.scene, W.camera);
  placeLabels(W);
}

/* ---------- the card: picture, labels, facts, buttons ---------- */

const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

function labelsFor(view) {
  if (view.view === "planet") {
    const f = view.focus[0];
    return f ? [f] : [];
  }
  if (view.view === "compare" || view.view === "sizes") return bodiesFor(view);
  if (view.view === "orbits" && view.focus.length) return ["sun", ...view.focus];
  return ["sun", ...ORBITING];
}

function placeLabels(W) {
  const card = W.card;
  const rect = card.stage.getBoundingClientRect();
  const v = new THREE.Vector3();
  for (const [name, label] of Object.entries(card.labels)) {
    const body = W.bodies[name];
    const wanted = card.labelNames.includes(name) && body.holder.visible;
    if (!wanted) { label.hidden = true; continue; }
    v.copy(body.pos).add(new THREE.Vector3(0, -body.scale * 1.15, 0)).project(W.camera);
    const slot = W.rowLayout ? W.rowLayout.findIndex((s) => s.name === name) : -1;
    const stagger = slot % 2 === 1 && W.rowLayout[slot].radius < 0.3 ? 14 : 0; // small neighbours: alternate rows
    const x = (v.x * 0.5 + 0.5) * rect.width, y = (-v.y * 0.5 + 0.5) * rect.height + stagger;
    label.hidden = v.z > 1 || x < -40 || x > rect.width + 40 || y < -20 || y > rect.height + 20;
    label.style.transform = `translate(${x}px, ${y}px) translate(-50%, 0)`;
    label.classList.toggle("on", W.view.focus.includes(name) || (W.lit === name && performance.now() < W.litUntil));
  }
}

function factRows(b) {
  const f = FACTS[b];
  const rows = [["Diameter", `${fmt(f.diameter)} km${b !== "earth" ? ` (${fmt(f.diameter / EARTH.diameter, 2)} × Earth)` : ""}`]];
  if (f.distance) rows.push(["From the Sun", `${fmt(f.distance)} million km (${fmt(f.distance / EARTH.distance, 2)} AU)`]);
  if (f.fromEarth) rows.push(["From Earth", `${fmt(f.fromEarth * 1000)} thousand km`]);
  if (f.year) rows.push([b === "moon" ? "Orbit" : "Year", f.year > 700 ? `${fmt(f.year / 365.25, 1)} Earth years` : `${fmt(f.year, 1)} Earth days`]);
  if (f.day) rows.push(["Day", f.day > 48 ? `${fmt(f.day / 24, 1)} Earth days` : `${fmt(f.day, 1)} hours`]);
  if (f.moons) rows.push(["Moons", f.moons]);
  rows.push([f.tempNote === "surface" ? "Surface" : "Average temp.", `${fmt(f.temp)} °C`]);
  rows.push(["Gravity", `${fmt(f.gravity, 1)} m/s²${b !== "earth" ? ` (${fmt(f.gravity / EARTH.gravity, 2)} × Earth)` : ""}`]);
  return rows;
}

const CAPTIONS = {
  overview: "The solar system: the Sun and its eight planets, moving at their real relative speeds. Sizes and distances are squeezed so everything fits.",
  orbits: "The orbits from above. Planets closer to the Sun go round much faster: Mercury circles four times while Earth goes round once.",
  sizes: "The eight planets at their true relative sizes.",
  compare: "Shown at their true relative sizes.",
};

function paintCard(card, view) {
  const focus = view.focus.filter((b) => FACTS[b]);
  card.labelNames = labelsFor(view);
  card.facts.replaceChildren();
  if (view.view === "planet" && focus[0]) {
    const f = FACTS[focus[0]];
    card.facts.append(el("h4", null, f.name), el("p", "kind", f.kind), el("p", "note", f.note));
    const dl = el("dl");
    for (const [k, v] of factRows(focus[0])) dl.append(el("dt", null, k), el("dd", null, v));
    card.facts.append(dl);
  } else if (view.view === "compare" && focus.length) {
    const table = el("table");
    const head = el("tr");
    head.append(el("th"), ...focus.map((b) => el("th", null, FACTS[b].name)));
    table.append(head);
    const rows = focus.map(factRows);
    const labels = [...new Set(rows.flat().map(([label]) => label))];
    for (const label of labels) {
      const values = rows.map((r) => (r.find((x) => x[0] === label) || [null, "—"])[1].replace(/ \(.*\)$/, ""));
      if (values.filter((v) => v !== "—").length < Math.min(2, focus.length)) continue;
      const tr = el("tr");
      tr.append(el("th", null, label), ...values.map((v) => el("td", null, v)));
      table.append(tr);
    }
    card.facts.append(el("h4", null, focus.map((b) => FACTS[b].name).join(" and ")), el("p", "note", CAPTIONS.compare), table);
  } else {
    card.facts.append(el("p", "note", CAPTIONS[view.view] || CAPTIONS.overview));
    if (focus[0]) {
      const f = FACTS[focus[0]];
      const dl = el("dl");
      // a size question only needs the size; the orbits view its distance and year
      for (const [k, v] of factRows(focus[0]).slice(0, view.view === "sizes" ? 1 : 4)) dl.append(el("dt", null, k), el("dd", null, v));
      card.facts.append(el("h4", null, f.name), dl);
    }
  }
  card.facts.append(el("p", "source", "Facts: NASA planetary fact sheet."));
  for (const [name, button] of Object.entries(card.buttons)) button.setAttribute("aria-pressed", String(view.view === name));
}

function buildCard(root, visual) {
  root.replaceChildren();
  root.classList.add("visual", "solar");
  const stage = el("div", "stage");
  const labelLayer = el("div", "labels");
  const labels = {};
  for (const b of ["sun", ...ORBITING, "moon"]) {
    const label = el("span", null, FACTS[b].name);
    label.hidden = true;
    labelLayer.append(label);
    labels[b] = label;
  }
  const facts = el("div", "facts");
  const tools = el("div", "tools");
  const buttons = {};
  for (const [name, text] of [["overview", "Whole system"], ["sizes", "Sizes"], ["orbits", "Orbits"]]) {
    const button = el("button", null, text);
    button.type = "button";
    button.addEventListener("click", () => { if (world && world.card === card) setView({ ...visual, view: name, focus: name === "overview" ? [] : visual.focus.filter((b) => b !== "sun" && b !== "moon") }); });
    tools.append(button);
    buttons[name] = button;
  }
  const hint = el("p", "hint", "Drag to turn, scroll to zoom, click a planet.");
  stage.append(labelLayer, tools, hint); // buttons live on the picture, facts beside or under it
  root.append(stage, facts);
  const card = { root, stage, labels, labelNames: [], facts, tools, buttons, visual };
  return card;
}

/* ---------- moving the one live view between answers ---------- */

function makeLive(root, visual) {
  if (!world) {
    try { world = buildWorld(); } catch {
      root.replaceChildren(el("p", "note", "This browser can't show 3D graphics, so the solar system view is hidden."));
      return;
    }
    attachControls(world);
  }
  const W = world;
  if (W.card && W.card.root !== root && W.card.root.isConnected) {
    try { freeze(W.card); } catch (problem) { console.warn("Solar system view: couldn't keep a still picture", problem); }
  }
  const card = buildCard(root, visual);
  W.card = card;
  W.visible = true;
  // Size and shape set here too, not only in styles.css: with an old cached stylesheet the canvas
  // and its frame kept resizing each other and grew without limit.
  Object.assign(card.stage.style, { position: "relative", aspectRatio: "16 / 10", overflow: "hidden" });
  Object.assign(W.renderer.domElement.style, { display: "block", width: "100%", height: "100%" });
  card.stage.prepend(W.renderer.domElement);
  W.observer?.disconnect();
  W.observer = new IntersectionObserver((entries) => { W.visible = entries.some((e) => e.isIntersecting); });
  W.observer.observe(root);
  W.resize?.disconnect();
  W.resize = new ResizeObserver(() => {
    const width = card.stage.getBoundingClientRect().width;
    const height = Math.round(width * 10 / 16); // from the width only, never from what the canvas did to the frame
    if (!width || !height) return;
    W.renderer.setSize(width, height, false);
    W.camera.aspect = width / height;
    W.camera.updateProjectionMatrix();
    W.size = { width, height };
    card.overlay = getComputedStyle(card.facts).position === "absolute"; // facts over the picture (wide) or under it (phones)
  });
  W.resize.observe(card.stage);
  setView(visual, { instant: !W.view });
  if (!W.running) { W.running = true; W.clock.getDelta(); requestAnimationFrame(tick); }
}

// An older answer keeps a still picture of its view; clicking it brings the live view back.
function freeze(card) {
  const W = world;
  W.renderer.render(W.scene, W.camera);
  const still = el("img", "still");
  still.alt = "Solar system view";
  try { still.src = W.renderer.domElement.toDataURL("image/jpeg", 0.85); } catch { /* keep it blank */ }
  card.tools.replaceChildren();
  card.stage.replaceChildren(still, card.tools);
  card.root.classList.add("frozen");
  const again = el("button", "again", "Show in 3D again");
  again.type = "button";
  again.addEventListener("click", () => makeLive(card.root, card.visual));
  card.tools.append(again);
}

function asleep(root, visual) { // an older answer in a reopened chat: no 3D until asked
  root.replaceChildren();
  root.classList.add("visual", "solar", "frozen", "asleep");
  const names = visual.focus.filter((b) => FACTS[b]).map((b) => FACTS[b].name).join(", ");
  const button = el("button", "again", `Show the solar system${names ? `: ${names}` : ""}`);
  button.type = "button";
  button.addEventListener("click", () => makeLive(root, visual));
  root.append(button);
}

function attachControls(W) {
  const canvas = W.renderer.domElement;
  let drag = null;
  canvas.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, moved: 0 }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    drag.x = e.clientX; drag.y = e.clientY;
    W.cam.yaw -= dx * 0.008;
    W.cam.pitch = clamp(W.cam.pitch - dy * 0.006, -1.1, 1.1);
    W.instant = false;
  });
  canvas.addEventListener("pointerup", (e) => {
    const click = drag && drag.moved < 6;
    drag = null;
    if (!click) return;
    const rect = canvas.getBoundingClientRect();
    const pointer = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    W.raycaster.setFromCamera(pointer, W.camera);
    const meshes = Object.values(W.bodies).filter((b) => b.holder.visible).map((b) => b.mesh);
    const hit = W.raycaster.intersectObjects(meshes, false)[0];
    if (hit) setView({ ...W.view, view: "planet", focus: [hit.object.userData.body] });
  });
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    W.cam.zoom = clamp(W.cam.zoom * Math.exp(e.deltaY * 0.001), 0.35, 2.5);
  }, { passive: false });
}

/* ---------- light up what the tutor is talking about ---------- */

function spokenBody(text) {
  const lower = (text || "").toLowerCase();
  let best = null;
  for (const [body, names] of Object.entries(SPOKEN)) {
    for (const n of names) {
      const i = lower.search(n.length > 3 && /^[a-z]+$/.test(n) ? new RegExp(`\\b${n}\\b`) : new RegExp(n));
      if (i >= 0 && (!best || i < best.i)) best = { body, i };
    }
  }
  return best && best.body;
}

function highlight(body) {
  if (!world || !body || !world.bodies[body]) return;
  world.lit = body;
  world.litUntil = performance.now() + 2200;
}

window.addEventListener("mentora:avatar", (event) => {
  const { type, text, charIndex } = event.detail || {};
  if (!world || !world.card) return;
  if (type === "word") highlight(spokenBody(((text || "").slice(charIndex || 0).match(/^\S+/) || [""])[0]));
  if (type === "speech-audio" || type === "speech-part") highlight(spokenBody(text));
});

window.addEventListener("mentora:visual", (event) => {
  const { type, element, visual, live } = event.detail || {};
  if (type !== "mount" || !element || !visual || visual.kind !== "solar_system") return;
  try {
    if (live) makeLive(element, visual); else asleep(element, visual);
  } catch (problem) {
    console.warn("Solar system view:", problem);
    element.replaceChildren();
  }
});

window.mentoraSolar = { get world() { return world; }, setView: (v) => world && setView(v), FACTS }; // for debugging and tests
