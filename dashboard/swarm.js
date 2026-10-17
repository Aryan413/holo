"use strict";

/* Mentora background animation. Plain JavaScript, no libraries, no build step.

   1. A swarm of ASCII characters drifts behind the whole app and follows the pointer.
      Faster characters are drawn denser (. : + # @) and turn brass; slow ones are blue.
   2. On the sign-in screen the swarm now and then pulls together into a turning ASCII globe,
      like a hologram, then lets go again.
   3. The "Mentora" title decodes out of random characters once, when the page opens.
   4. The tutor's "Thinking..." gets a small ASCII loading bar.

   With "reduce motion" switched on in the system, nothing moves: one still frame is drawn. */

(function () {
  const RAMP = " .:-=+*#%@"; // light to dense
  const SCRAMBLE = "01#@%&*+=<>/\\|{}[]";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  const canvas = document.createElement("canvas");
  canvas.id = "swarm";
  canvas.setAttribute("aria-hidden", "true");
  document.body.prepend(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const COUNT = 230;
  const GOLDEN = 2.399963; // golden angle, spreads points evenly over a sphere
  const bits = Array.from({ length: COUNT }, (_, i) => ({ x: 0, y: 0, vx: 0, vy: 0, i }));
  let w = 0;
  let h = 0;
  let fontPx = 15;
  let colors = { ghost: "#9ed0e6", lamp: "#f0b95a" };
  const pointer = { x: 0, y: 0, seen: -1e9 };

  function readColors() {
    const css = getComputedStyle(document.documentElement);
    colors = {
      ghost: css.getPropertyValue("--ghost").trim() || colors.ghost,
      lamp: css.getPropertyValue("--lamp").trim() || colors.lamp,
    };
  }

  function resize() {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const oldW = w || 1;
    const oldH = h || 1;
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    fontPx = w < 600 ? 13 : 15;
    for (const b of bits) {
      b.x = oldW === 1 ? Math.random() * w : (b.x / oldW) * w;
      b.y = oldH === 1 ? Math.random() * h : (b.y / oldH) * h;
    }
    readColors();
    if (reduce) drawStill();
  }

  /* ---------- the globe the swarm sometimes becomes ---------- */

  function globe(t) {
    const wide = w > 820;
    const cx = wide ? w * 0.26 : w * 0.5;
    const cy = wide ? h * 0.5 : h * 0.3;
    const radius = (wide ? Math.min(w * 0.2, h * 0.3) : Math.min(w * 0.3, h * 0.18)) * (1 + 0.025 * Math.sin(t * 0.002));
    const spin = t * 0.0005;
    const tilt = 0.4;
    const cs = Math.cos(spin);
    const sn = Math.sin(spin);
    const ct = Math.cos(tilt);
    const st = Math.sin(tilt);
    return bits.map((b) => {
      const y = 1 - (b.i / (COUNT - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const a = b.i * GOLDEN;
      const x0 = Math.cos(a) * r;
      const z0 = Math.sin(a) * r;
      const x1 = x0 * cs + z0 * sn;
      const z1 = -x0 * sn + z0 * cs;
      return {
        x: cx + x1 * radius,
        y: cy + (y * ct - z1 * st) * radius,
        depth: y * st + z1 * ct, // -1 far side, +1 near side
      };
    });
  }

  /* ---------- drawing ---------- */

  function setFont() {
    ctx.font = `${fontPx}px ui-monospace, Consolas, "Courier New", monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
  }

  function drawStill() {
    ctx.clearRect(0, 0, w, h);
    setFont();
    ctx.fillStyle = colors.ghost;
    ctx.globalAlpha = 0.22;
    for (const b of bits) ctx.fillText(RAMP[1 + (b.i % 6)], b.x, b.y);
    ctx.globalAlpha = 1;
  }

  let last = 0;
  let form = 0; // 0 = free swarm, 1 = globe
  let frames = 0;

  function frame(t) {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (t - last) / 1000 || 0.016);
    last = t;
    if (++frames % 180 === 0) readColors();

    const onSignIn = !!document.querySelector(".auth");
    const seconds = t / 1000;
    const wantGlobe = onSignIn && seconds % 18 > 8 && seconds % 18 < 15;
    form += ((wantGlobe ? 1 : 0) - form) * Math.min(1, dt * 1.6);
    const targets = form > 0.01 ? globe(t) : null;

    // where the swarm is drawn to: the pointer while it moves, otherwise a slow wandering point
    const pointerActive = t - pointer.seen < 4000;
    const ax = pointerActive ? pointer.x : w * (0.5 + 0.32 * Math.sin(t * 0.00031));
    const ay = pointerActive ? pointer.y : h * (0.5 + 0.3 * Math.cos(t * 0.00043));
    const pull = pointerActive ? 1 : 0.45;

    ctx.globalCompositeOperation = "destination-out";
    ctx.fillStyle = "rgba(0, 0, 0, 0.2)"; // old glyphs fade out, leaving short trails
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "source-over";
    setFont();

    const base = onSignIn ? 0.8 : 0.26; // quieter once the person is reading or typing

    for (const b of bits) {
      // flow field: a smooth, slowly changing wind
      const angle = Math.sin(b.x * 0.004 + t * 0.0004) * Math.cos(b.y * 0.0037 - t * 0.0003) * Math.PI * 2;
      let fx = Math.cos(angle) * 55;
      let fy = Math.sin(angle) * 55;

      // gentle orbit around the attractor
      const dx = ax - b.x;
      const dy = ay - b.y;
      const dist = Math.hypot(dx, dy) + 1;
      const strength = (pull * 520) / (dist + 140);
      fx += (dx / dist) * strength * 60 + (-dy / dist) * strength * 40;
      fy += (dy / dist) * strength * 60 + (dx / dist) * strength * 40;

      let depth = 0;
      if (targets) {
        const tg = targets[b.i];
        fx = fx * (1 - form) + (tg.x - b.x) * 7 * form;
        fy = fy * (1 - form) + (tg.y - b.y) * 7 * form;
        depth = tg.depth;
      }

      b.vx += fx * dt;
      b.vy += fy * dt;
      const damping = Math.max(0, 1 - (1.5 + 3.5 * form) * dt);
      b.vx *= damping;
      b.vy *= damping;
      const speed = Math.hypot(b.vx, b.vy);
      if (speed > 260) { b.vx *= 260 / speed; b.vy *= 260 / speed; }
      b.x += b.vx * dt;
      b.y += b.vy * dt;

      if (form < 0.5) { // wrap around the edges while swarming
        if (b.x < -20) b.x = w + 20; else if (b.x > w + 20) b.x = -20;
        if (b.y < -20) b.y = h + 20; else if (b.y > h + 20) b.y = -20;
      }

      // fast = dense and brass; on the globe, near side = dense and bright
      const swarmIdx = 1 + Math.min(8, Math.floor(speed / 28));
      const globeIdx = 1 + Math.round(((depth + 1) / 2) * 8);
      const idx = Math.round(swarmIdx * (1 - form) + globeIdx * form);
      const shade = (1 - form) + form * (0.3 + 0.7 * ((depth + 1) / 2));
      ctx.globalAlpha = clamp(base * shade, 0, 1);
      ctx.fillStyle = speed > 140 && form < 0.5 ? colors.lamp : colors.ghost;
      ctx.fillText(RAMP[clamp(idx, 1, 9)], b.x, b.y);
    }
    ctx.globalAlpha = 1;
  }

  /* ---------- title: decode out of random characters, once ---------- */

  function decode(el, finalText) {
    const start = performance.now();
    const duration = 900;
    function step(now) {
      const shown = Math.floor(clamp((now - start) / duration, 0, 1) * finalText.length);
      let text = finalText.slice(0, shown);
      for (let i = shown; i < finalText.length; i++) {
        text += SCRAMBLE[Math.floor(Math.random() * SCRAMBLE.length)];
      }
      el.textContent = text;
      el.setAttribute("data-text", text); // keeps the mirrored reflection in step
      if (shown < finalText.length) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* ---------- tutor "Thinking..." gets a loading bar ---------- */

  const BAR = ["[=    ]", "[==   ]", "[===  ]", "[ === ]", "[  ===]", "[   ==]", "[    =]", "[   ==]", "[  ===]", "[ === ]", "[===  ]", "[==   ]"];

  /* ---------- start ---------- */

  window.addEventListener("resize", resize);
  window.addEventListener("pointermove", (e) => {
    pointer.x = e.clientX;
    pointer.y = e.clientY;
    pointer.seen = performance.now();
  }, { passive: true });
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", readColors);
  resize();

  if (!reduce) {
    requestAnimationFrame(frame);

    const rootEl = document.getElementById("root");
    let decoded = false;
    if (rootEl) {
      new MutationObserver(() => {
        if (decoded) return;
        const mark = rootEl.querySelector(".wordmark");
        if (!mark) return;
        decoded = true;
        decode(mark, mark.textContent);
      }).observe(rootEl, { childList: true });
    }

    let tick = 0;
    setInterval(() => {
      const label = document.querySelectorAll(".thinking");
      if (!label.length) return;
      tick = (tick + 1) % BAR.length;
      for (const el of label) el.textContent = `Thinking ${BAR[tick]}`;
    }, 110);
  }
})();
