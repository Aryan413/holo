/* Mentora's 3D tutor beside the chat: a VRM character that lip-syncs to the spoken answer and
   changes expression with what the tutor is doing (listening, thinking, speaking, pleased, sorry).

   app.js only announces what is happening, as "mentora:avatar" events on window; this file draws.
   It is decoration: if WebGL, the model or anything else here fails, the chat works exactly as before.
   To change the character, replace models/tutor.vrm with any VRM 1.0 or 0.x model. */

import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";

const MODEL_URL = "models/tutor.vrm";
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const VISEMES = ["aa", "ih", "ou", "ee", "oh"];
const MOODS = ["happy", "sad", "surprised", "relaxed", "angry"];

// Resting face for each thing the tutor can be doing. Kept light so the lips stay readable.
const FACES = {
  idle: { relaxed: 0.2 },
  listening: { happy: 0.15 },
  transcribing: { relaxed: 0.15 },
  thinking: { relaxed: 0.3 },
  speaking: { happy: 0.12 },
};

const avatar = {
  state: "idle", // idle | listening | transcribing | thinking | speaking
  speaking: false,
  paused: false,
  curious: false, // the sentence being read is a question
  audio: null, // realistic voice: the <audio> playing now
  envelope: null, // ...and how loud and how "sharp" it is, frame by frame
  word: null, // browser voice: mouth shapes for the word being read { start, duration, shapes }
  lastWordAt: 0,
  mood: {}, // a passing feeling on top of the resting face, e.g. { happy: 0.7 }
  moodUntil: 0,
  vrm: null,
};
window.mentoraAvatar = avatar; // handy when debugging in the browser console

let renderer = null;
let scene = null;
let camera = null;
let lookTarget = null;
let stage = null;
let loading = null;
let failure = "";
let running = false;
let resizeObserver = null;
const clock = new THREE.Clock();
const face = Object.fromEntries([...VISEMES, ...MOODS].map((name) => [name, 0]));
const gaze = { x: 0, y: 0, tx: 0, ty: 0, nextSaccade: 0 };
const pointer = { x: 0, y: 0 };
let nextBlink = 2;
let blinkStart = -1;

class FriendlyError extends Error {}

/* ---------- stage and model ---------- */

function note(text) {
  if (!stage) return;
  let p = stage.querySelector(".stage-note");
  if (!p) {
    p = document.createElement("p");
    p.className = "stage-note";
    stage.append(p);
  }
  p.textContent = text;
  p.hidden = !text;
}

function setUpRenderer() {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(24, 1, 0.05, 20);
  // Toon-shaded VRM models want about one light's worth (three.js lights are physical: PI is "1").
  const key = new THREE.DirectionalLight(0xffffff, Math.PI * 0.8);
  key.position.set(0.4, 1, 1.2);
  const rim = new THREE.DirectionalLight(0x8fd8ff, Math.PI * 0.35); // a cool back light for the hologram look
  rim.position.set(-1, 1, -1.2);
  scene.add(key, rim, new THREE.AmbientLight(0xffffff, 0.25));
  lookTarget = new THREE.Object3D(); // what the eyes follow; moved around the camera
  camera.add(lookTarget);
  scene.add(camera);
}

async function loadModel() {
  const response = await fetch(MODEL_URL);
  if (!response.ok) throw new FriendlyError("The tutor's 3D model is missing (dashboard/models/tutor.vrm).");
  const data = await response.arrayBuffer();
  if (new TextDecoder().decode(data.slice(0, 40)).startsWith("version https://git-lfs")) {
    throw new FriendlyError("The tutor's 3D model wasn't downloaded. In the project folder run: git lfs install, then git lfs pull.");
  }
  const loader = new GLTFLoader();
  loader.register((parser) => new VRMLoaderPlugin(parser));
  const gltf = await loader.parseAsync(data, "models/");
  const vrm = gltf.userData.vrm;
  if (!vrm) throw new FriendlyError("models/tutor.vrm isn't a VRM character model.");
  VRMUtils.removeUnnecessaryVertices(gltf.scene);
  VRMUtils.combineSkeletons(gltf.scene);
  VRMUtils.rotateVRM0(vrm); // older VRM 0.x models face away; turn them to the camera
  vrm.scene.traverse((object) => { object.frustumCulled = false; });
  scene.add(vrm.scene);
  restPose(vrm);
  vrm.lookAt.target = lookTarget;
  vrm.update(0);
  frameCamera(vrm);
  return vrm;
}

function bone(vrm, name) {
  return vrm.humanoid.getNormalizedBoneNode(name);
}

function restPose(vrm) {
  // Models come in a T-pose: bring the arms down to the sides.
  bone(vrm, "leftUpperArm")?.rotation.set(0, 0, -1.2);
  bone(vrm, "rightUpperArm")?.rotation.set(0, 0, 1.2);
  bone(vrm, "leftLowerArm")?.rotation.set(0, 0, -0.12);
  bone(vrm, "rightLowerArm")?.rotation.set(0, 0, 0.12);
}

// Head to waist, whatever the panel's shape: back off until both the width and the height fit.
const VIEW = { width: 0.48, height: 0.6, above: 0.25 }; // metres around the character; space above the head bone
let headPosition = null;

function frameCamera(vrm) {
  if (vrm) {
    vrm.scene.updateMatrixWorld(true);
    headPosition = bone(vrm, "head").getWorldPosition(new THREE.Vector3());
  }
  if (!headPosition) return;
  const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  const distance = Math.max(VIEW.height / 2 / tanV, VIEW.width / 2 / (tanV * camera.aspect));
  const centreY = headPosition.y + VIEW.above - distance * tanV; // keeps the top of the head near the top edge
  camera.position.set(headPosition.x, centreY, headPosition.z + distance);
  camera.lookAt(headPosition.x, centreY, headPosition.z);
}

function resize() {
  if (!stage || !renderer) return;
  const width = stage.clientWidth;
  const height = stage.clientHeight;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  frameCamera();
}

function mount(element) {
  if (!element) return;
  stage = element;
  if (failure) { note(failure); return; }
  try {
    if (!renderer) setUpRenderer();
  } catch {
    failure = "This browser can't show 3D graphics, so the tutor character is hidden.";
    note(failure);
    return;
  }
  stage.prepend(renderer.domElement);
  resizeObserver?.disconnect();
  resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(stage);
  resize();
  if (!avatar.vrm) {
    note("Loading the tutor…");
    loading ||= loadModel()
      .then((vrm) => { avatar.vrm = vrm; resize(); note(""); })
      .catch((problem) => {
        failure = problem instanceof FriendlyError ? problem.message : "The tutor character couldn't be shown on this computer.";
        if (!(problem instanceof FriendlyError)) console.warn("Tutor character failed to load", problem);
        note(failure);
      });
  }
  if (!running) { running = true; clock.getDelta(); requestAnimationFrame(tick); }
}

/* ---------- lip sync ---------- */

// Realistic voice: decode a copy of the audio and measure each 1/60 s. The playing <audio> itself is
// never touched, so this can't mute or interrupt the voice.
async function analyse(audio) {
  const encoded = await (await fetch(audio.src)).arrayBuffer();
  const decoded = await new OfflineAudioContext(1, 1, 44100).decodeAudioData(encoded);
  const samples = decoded.getChannelData(0);
  const hop = Math.max(1, Math.round(decoded.sampleRate / 60));
  const frames = [];
  for (let start = 0; start < samples.length; start += hop) {
    let energy = 0;
    let crossings = 0;
    const end = Math.min(samples.length, start + hop);
    for (let i = start; i < end; i += 1) {
      energy += samples[i] * samples[i];
      if (i > start && (samples[i] >= 0) !== (samples[i - 1] >= 0)) crossings += 1;
    }
    frames.push({ rms: Math.sqrt(energy / (end - start)), hz: (crossings * decoded.sampleRate) / (end - start) });
  }
  const loudest = [...frames].map((f) => f.rms).sort((a, b) => a - b)[Math.floor(frames.length * 0.95)] || 1;
  const shapes = frames.map((f) => ({
    open: clamp((f.rms - loudest * 0.08) / (loudest * 0.75), 0, 1),
    // How often the wave crosses zero, per second. Measured on real speech: most vowels 800-2500,
    // "s" and "ee" sounds above 4500, dark "oo"/"oh" vowels below about 1000.
    hz: f.hz,
  }));
  return { at: (time) => shapes[Math.min(shapes.length - 1, Math.floor(time * 60))] };
}

// Browser voice: only the words are known, so shape the mouth from the word's vowels.
const LETTER_SHAPES = { a: "aa", e: "ee", i: "ih", y: "ih", o: "oh", u: "ou", w: "ou" };

function wordShapes(word) {
  const shapes = [];
  for (const letter of word.toLowerCase()) {
    if (LETTER_SHAPES[letter]) shapes.push({ [LETTER_SHAPES[letter]]: 0.85 });
    else if ("mbp".includes(letter)) shapes.push({}); // lips together
    else if (/[a-z]/.test(letter)) shapes.push({ aa: 0.25 });
    else if (/[ഀ-ൿ]/.test(letter)) shapes.push({ [VISEMES[letter.charCodeAt(0) % VISEMES.length]]: 0.7 }); // Malayalam
  }
  return shapes.length ? shapes : [{ aa: 0.5 }];
}

function mouthTarget(t) {
  const target = {};
  if (!avatar.speaking || avatar.paused) return target;
  const { audio } = avatar;
  if (audio) {
    if (audio.paused || audio.ended) return target;
    if (!avatar.envelope) return babble(t); // still measuring the audio
    const shape = avatar.envelope.at(audio.currentTime);
    if (!shape) return target;
    if (shape.hz > 4500) Object.assign(target, { ee: shape.open * 0.65, ih: shape.open * 0.45 });
    else if (shape.hz < 1000) Object.assign(target, { oh: shape.open * 0.7, ou: shape.open * 0.4 });
    else target.aa = shape.open;
    return target;
  }
  const now = performance.now();
  const { word } = avatar;
  if (word && now - word.start < word.duration) {
    const i = Math.floor(((now - word.start) / word.duration) * word.shapes.length);
    return { ...word.shapes[Math.min(i, word.shapes.length - 1)] };
  }
  // Some voices never say which word they are on: keep the mouth moving while they talk.
  if (now - avatar.lastWordAt > 900) return babble(t);
  return target;
}

function babble(t) {
  const open = 0.25 + 0.4 * Math.abs(Math.sin(t * 9.5) * Math.sin(t * 3.7 + 1));
  return Math.sin(t * 2.3) > 0.4 ? { oh: open * 0.8 } : { aa: open };
}

/* ---------- face, gaze and body ---------- */

function setState(state) {
  avatar.state = state;
}

function feel(mood, seconds) {
  avatar.mood = mood;
  avatar.moodUntil = performance.now() + seconds * 1000;
}

function moodOf(text) {
  const t = text.toLowerCase();
  if (/\b(great|well done|excellent|exactly|correct|nice work|good job|perfect|congratulations|brilliant)\b/.test(t)) return { happy: 0.7 };
  if (/\b(sorry|unfortunately|not quite|incorrect|mistake|wrong)\b/.test(t)) return { sad: 0.35 };
  if (/\b(wow|amazing|interesting|fascinating|surprising|imagine)\b/.test(t)) return { surprised: 0.3 };
  return { happy: 0.3 };
}

function updateFace(dt, t) {
  const vrm = avatar.vrm;
  const mouth = mouthTarget(t);
  const resting = FACES[avatar.state] || FACES.idle;
  const now = performance.now();
  const passing = now < avatar.moodUntil ? avatar.mood : {};
  const talking = avatar.speaking && !avatar.paused;
  const ease = Math.min(1, dt * 14);
  const moodEase = Math.min(1, dt * 4);
  for (const name of VISEMES) {
    face[name] += ((mouth[name] || 0) - face[name]) * ease;
    vrm.expressionManager.setValue(name, face[name]);
  }
  for (const name of MOODS) {
    let target = Math.max(resting[name] || 0, passing[name] || 0);
    if (name === "surprised" && talking && avatar.curious) target = Math.max(target, 0.2); // asking a question
    if (talking) target = Math.min(target, 0.35); // strong feelings would hide the lips
    face[name] += (target - face[name]) * moodEase;
    vrm.expressionManager.setValue(name, face[name]);
  }
  // Blink every few seconds (not while smiling broadly: happy eyes are already closed).
  if (t > nextBlink && blinkStart < 0) blinkStart = t;
  let blink = 0;
  if (blinkStart >= 0) {
    const k = (t - blinkStart) / 0.16;
    blink = k < 0.5 ? k * 2 : Math.max(0, 2 - k * 2);
    if (k >= 1) { blinkStart = -1; nextBlink = t + 2 + Math.random() * 4; }
  }
  vrm.expressionManager.setValue("blink", face.happy > 0.5 ? 0 : blink);
}

function updateGaze(dt, t) {
  // Look at the student, glance up and aside while thinking, follow the pointer a little when idle.
  let x = 0;
  let y = 0;
  if (avatar.state === "thinking") { x = 0.35; y = 0.3; }
  else if (avatar.state === "idle" && !reduceMotion) { x = pointer.x * 0.25; y = pointer.y * 0.15; }
  if (t > gaze.nextSaccade) { // small natural eye jumps
    gaze.tx = (Math.random() - 0.5) * 0.08;
    gaze.ty = (Math.random() - 0.5) * 0.05;
    gaze.nextSaccade = t + 1 + Math.random() * 2.5;
  }
  const ease = Math.min(1, dt * 5);
  gaze.x += (x + gaze.tx - gaze.x) * ease;
  gaze.y += (y + gaze.ty - gaze.y) * ease;
  lookTarget.position.set(gaze.x, gaze.y, 0);
}

function updateBody(dt, t) {
  const vrm = avatar.vrm;
  const head = bone(vrm, "head");
  const neck = bone(vrm, "neck");
  const chest = bone(vrm, "chest") || bone(vrm, "spine");
  const calm = reduceMotion ? 0 : 1;
  const talking = avatar.speaking && !avatar.paused;
  const tilt = { thinking: 0.1, listening: -0.08 }[avatar.state] || 0;
  const nod = talking ? (face.aa + face.oh) * 0.05 + Math.sin(t * 2.1) * 0.02 * calm : 0;
  if (chest) chest.rotation.x = Math.sin(t * 1.5) * 0.012 * calm; // breathing
  if (neck) neck.rotation.y = Math.sin(t * 0.45) * 0.04 * calm;
  if (head) {
    head.rotation.z += (tilt + Math.sin(t * 0.6) * 0.02 * calm - head.rotation.z) * Math.min(1, dt * 3);
    head.rotation.x += (nod + (avatar.state === "listening" ? 0.05 : 0) - head.rotation.x) * Math.min(1, dt * 6);
  }
}

function tick() {
  if (!stage || !stage.isConnected) { running = false; return; }
  requestAnimationFrame(tick);
  const dt = Math.min(clock.getDelta(), 0.1);
  if (!avatar.vrm || stage.hidden || document.hidden) return;
  const t = clock.elapsedTime;
  updateFace(dt, t);
  updateGaze(dt, t);
  updateBody(dt, t);
  avatar.vrm.update(dt);
  renderer.render(scene, camera);
}

function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}

/* ---------- what app.js tells us ---------- */

function startPart(text) {
  avatar.speaking = true;
  avatar.paused = false;
  avatar.curious = /\?\s*$/.test(text || "");
  avatar.word = null;
  avatar.lastWordAt = performance.now(); // give the voice a moment before falling back to babble
  setState("speaking");
}

const handlers = {
  mount: (d) => mount(d.element),
  listening: () => setState("listening"),
  transcribing: () => setState("transcribing"),
  "mic-idle": () => { if (avatar.state === "listening" || avatar.state === "transcribing") setState("idle"); },
  thinking: () => setState("thinking"),
  answer: (d) => { setState("idle"); feel(moodOf(d.text || ""), 4); },
  oops: () => { setState("idle"); feel({ sad: 0.45 }, 2.5); },
  "speech-part": (d) => { avatar.audio = null; avatar.envelope = null; startPart(d.text); },
  "speech-audio": (d) => {
    startPart(d.text);
    const { audio } = d;
    avatar.audio = audio;
    avatar.envelope = null;
    analyse(audio).then((envelope) => { if (avatar.audio === audio) avatar.envelope = envelope; }).catch(() => {});
  },
  word: (d) => {
    const word = ((d.text || "").slice(d.charIndex || 0).match(/^\S+/) || [""])[0].replace(/[^\p{L}\p{N}]/gu, "");
    if (!word) return;
    const shapes = wordShapes(word);
    avatar.word = { start: performance.now(), duration: clamp(word.length * 70, 180, 750), shapes };
    avatar.lastWordAt = performance.now();
  },
  "speech-pause": () => { avatar.paused = true; },
  "speech-resume": () => { avatar.paused = false; avatar.lastWordAt = performance.now(); },
  "speech-stop": () => {
    avatar.speaking = false;
    avatar.paused = false;
    avatar.audio = null;
    avatar.envelope = null;
    avatar.word = null;
    if (avatar.state === "speaking") setState("idle");
  },
};

window.addEventListener("mentora:avatar", (event) => {
  const { type, ...detail } = event.detail || {};
  try { handlers[type]?.(detail); } catch (problem) { console.warn("Tutor character:", problem); }
});
window.addEventListener("pointermove", (event) => {
  pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
  pointer.y = -((event.clientY / window.innerHeight) * 2 - 1);
}, { passive: true });

// The tutor page may already be on screen if this file loaded after app.js drew it.
const existing = document.querySelector(".tutor-stage:not([hidden])");
if (existing) mount(existing);
