/* ============================================================
   Saga X Agent Desk — AgentAvatar (Three.js)

   One reusable renderer for all five agents. Progressive enhancement,
   not replacement: the SVG avatar renders first and stays in the DOM.
   A canvas is mounted over it only once a model has actually loaded, so
   every failure path — no WebGL, no model configured, CDN blocked,
   corrupt GLB — leaves the working desk exactly as it was.

   That ordering is the whole safety design. The desk is live and Abang
   uses it; a 3D upgrade must not be able to take it down.

   Loaded as a module so Three.js can be imported from a CDN without a
   build step, matching a project that has no package.json and no
   bundler. The classic scripts keep working alongside it.
   ============================================================ */

const CDN = "https://cdn.jsdelivr.net/npm/three@0.180.0";
const IDLE_FPS = 30;          // avatars do not need 60fps to breathe
const MAX_PIXEL_RATIO = 1.75; // retina at full ratio costs more than it shows

let THREE = null;
let GLTFLoader = null;
const instances = new Map();

// ── Capability checks ───────────────────────────────────────────

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext &&
      (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (err) {
    return false;
  }
}

// Respect the OS setting. An avatar that sways continuously is exactly
// what "reduce motion" is asking us not to do.
const reduceMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Data saver and 2G: a multi-megabyte GLB is the wrong thing to fetch.
function connectionTooSlow() {
  const c = navigator.connection;
  if (!c) return false;
  return c.saveData === true || /(^|-)2g$/.test(c.effectiveType || "");
}

async function loadThree() {
  if (THREE) return true;
  try {
    THREE = await import(`${CDN}/build/three.module.js`);
    ({ GLTFLoader } = await import(`${CDN}/examples/jsm/loaders/GLTFLoader.js`));
    return true;
  } catch (err) {
    console.warn("[avatar3d] Three.js unavailable, keeping SVG avatars:", err);
    return false;
  }
}

// ── One avatar ──────────────────────────────────────────────────

class AgentAvatar {
  constructor(host, agentId, cfg) {
    this.host = host;
    this.agentId = agentId;
    this.cfg = cfg;
    this.state = "idle";
    this.speaking = false;
    this.amplitude = 0;
    this.running = false;
    this.lastFrame = 0;
    this.blinkAt = performance.now() + 2000 + Math.random() * 3000;
    this.morphs = new Map();
    this.disposables = [];
  }

  async mount() {
    const { camera } = this.cfg;
    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(camera.fov, 1, 0.1, 20);
    this.camera.position.set(0, camera.y, camera.z);
    this.camera.lookAt(0, camera.y - 0.05, 0);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true, alpha: true, powerPreference: "low-power",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, MAX_PIXEL_RATIO));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    // Lighting tuned to the dashboard's own palette so the avatar sits
    // in the card rather than looking pasted onto it.
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(0.6, 1.4, 1.2);
    const rim = new THREE.DirectionalLight(
      new THREE.Color(this.cfg.accent || "#ffb3d9"), 1.1);
    rim.position.set(-1.1, 0.9, -0.8);
    this.scene.add(key, rim, new THREE.AmbientLight(0xb3a5ff, 0.9));
    this.disposables.push(key, rim);

    const gltf = await new Promise((resolve, reject) => {
      new GLTFLoader().load(this.cfg.model, resolve, undefined, reject);
    });

    this.model = gltf.scene;
    this.model.position.set(0, 0, 0);
    this.scene.add(this.model);

    // Index every morph target once, so lip-sync is a dictionary lookup
    // per frame instead of a mesh walk.
    this.model.traverse((o) => {
      if (o.isMesh && o.morphTargetDictionary) {
        for (const [name, idx] of Object.entries(o.morphTargetDictionary)) {
          if (!this.morphs.has(name)) this.morphs.set(name, []);
          this.morphs.get(name).push({ mesh: o, index: idx });
        }
      }
    });
    this.hasVisemes = window.SAGAX_3D.VISEMES.some((v) => this.morphs.has(v));

    if (gltf.animations && gltf.animations.length) {
      this.mixer = new THREE.AnimationMixer(this.model);
      this.clips = {};
      for (const clip of gltf.animations) {
        this.clips[clip.name.toLowerCase()] = this.mixer.clipAction(clip);
      }
      const first = Object.values(this.clips)[0];
      if (first) first.play();
    }

    // Only now does anything visible change.
    this.host.appendChild(this.renderer.domElement);
    this.renderer.domElement.className = "avatar-3d";
    this.host.classList.add("has-3d");

    this.resize();
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(this.host);

    return this;
  }

  resize() {
    const r = this.host.getBoundingClientRect();
    const w = Math.max(1, r.width), h = Math.max(1, r.height);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  setMorph(name, value) {
    const targets = this.morphs.get(name);
    if (!targets) return;
    for (const t of targets) {
      t.mesh.morphTargetInfluences[t.index] = value;
    }
  }

  setState(state) {
    if (state === this.state) return;
    this.state = state;
    const b = window.SAGAX_3D.STATE_BEHAVIOUR[state];
    if (!b) return;
    if (this.clips && b.clip && this.clips[b.clip]) {
      for (const a of Object.values(this.clips)) a.fadeOut(0.3);
      this.clips[b.clip].reset().fadeIn(0.3).play();
    }
    this.setMorph("browInnerUp", b.brow || 0);
    this.setMorph("mouthSmileLeft", b.smile || 0);
    this.setMorph("mouthSmileRight", b.smile || 0);
  }

  /** Amplitude 0..1 from the speech audio. The first working lip-sync
   *  layer; visemes refine it when the model has them. */
  setSpeaking(on, amplitude = 0) {
    this.speaking = on;
    this.amplitude = on ? amplitude : 0;
    if (!on) {
      this.setMorph("jawOpen", 0);
      for (const v of window.SAGAX_3D.VISEMES) this.setMorph(v, 0);
    }
  }

  frame(now) {
    if (!this.running) return;
    requestAnimationFrame((t) => this.frame(t));
    if (now - this.lastFrame < 1000 / IDLE_FPS) return;
    const dt = (now - this.lastFrame) / 1000;
    this.lastFrame = now;

    if (this.mixer) this.mixer.update(dt);

    const b = window.SAGAX_3D.STATE_BEHAVIOUR[this.state] || {};
    if (b.sway && !reduceMotion()) {
      this.model.rotation.y = Math.sin(now / 2200) * 0.06 * b.sway;
    }

    if (b.blink && now > this.blinkAt) {
      const phase = (now - this.blinkAt) / 120;
      const v = phase < 1 ? Math.sin(phase * Math.PI) : 0;
      this.setMorph("eyeBlinkLeft", v);
      this.setMorph("eyeBlinkRight", v);
      if (phase >= 1) this.blinkAt = now + 2500 + Math.random() * 4000;
    }

    if (this.speaking) {
      const a = Math.min(1, Math.max(0, this.amplitude));
      this.setMorph("jawOpen", a * 0.55);
      this.setMorph("mouthFunnel", a * 0.2);
    }

    this.renderer.render(this.scene, this.camera);
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.lastFrame = performance.now();
    requestAnimationFrame((t) => this.frame(t));
  }

  stop() { this.running = false; }

  /** Free GPU memory. Cards are re-rendered on state change, and a
   *  renderer left behind leaks a WebGL context — browsers cap those at
   *  around 16, so a few reloads would blank every avatar. */
  dispose() {
    this.stop();
    if (this.observer) this.observer.disconnect();
    if (this.mixer) this.mixer.stopAllAction();
    this.scene?.traverse((o) => {
      if (o.isMesh) {
        o.geometry?.dispose();
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of mats) {
          if (!m) continue;
          for (const k of Object.keys(m)) {
            if (m[k] && m[k].isTexture) m[k].dispose();
          }
          m.dispose();
        }
      }
    });
    for (const d of this.disposables) d.dispose?.();
    this.renderer?.dispose();
    this.renderer?.domElement?.remove();
    this.host?.classList.remove("has-3d");
  }
}

// ── Public surface ──────────────────────────────────────────────

async function mountAgent(agentId) {
  const cfg = window.SAGAX_3D?.AGENTS_3D?.[agentId];
  if (!cfg || !cfg.model) return null;           // no model yet — SVG stays
  if (instances.has(agentId)) return instances.get(agentId);

  const host = document.querySelector(
    `.card[data-agent="${agentId}"] .avatar-wrap`);
  if (!host) return null;

  try {
    const av = new AgentAvatar(host, agentId, cfg);
    await av.mount();
    instances.set(agentId, av);
    av.start();
    return av;
  } catch (err) {
    console.warn(`[avatar3d] ${agentId} failed, SVG retained:`, err);
    return null;
  }
}

async function init() {
  if (!webglAvailable()) {
    console.info("[avatar3d] no WebGL — SVG avatars retained");
    return;
  }
  if (connectionTooSlow()) {
    console.info("[avatar3d] data saver or 2G — skipping 3D");
    return;
  }
  const configured = Object.entries(window.SAGAX_3D?.AGENTS_3D || {})
    .filter(([, c]) => c.model);
  if (!configured.length) return;      // nothing to load; do not fetch Three.js

  if (!(await loadThree())) return;
  for (const [id] of configured) await mountAgent(id);
}

// Pause rendering when the desk is not on screen. Spec: do not render
// hidden avatars.
document.addEventListener("visibilitychange", () => {
  for (const av of instances.values()) {
    document.hidden ? av.stop() : av.start();
  }
});

window.SagaXAvatar3D = {
  init,
  mountAgent,
  setState: (id, s) => instances.get(id)?.setState(s),
  setSpeaking: (id, on, amp) => instances.get(id)?.setSpeaking(on, amp),
  disposeAll: () => {
    for (const av of instances.values()) av.dispose();
    instances.clear();
  },
  active: () => [...instances.keys()],
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
