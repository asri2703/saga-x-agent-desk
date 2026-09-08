/* ============================================================
   Saga X Agent Desk — agent 3D configuration

   Deliberately separate from the renderer so adding an agent is a data
   change, not a code change (spec requirement 6 and phase 7). One
   component renders all five; nothing here is specific to Putri.

   `model` is null until a GLB exists. Null is not a failure state — the
   SVG avatar stays, which is the documented fallback (requirement 12).

   Ready Player Me shut down on 31 January 2026 after the Netflix
   acquisition, so the URLs in the original spec cannot be fetched. The
   replacement must ship the ARKit 52-blendshape set; Avaturn does, and
   the viseme names below are the same either way.
   ============================================================ */

(() => {
  "use strict";

  // ARKit blendshape names used for lip-sync. Standard across every
  // provider that claims ARKit compatibility, so the mapping does not
  // change when the model source does.
  const ARKIT = {
    jawOpen: "jawOpen",
    mouthClose: "mouthClose",
    mouthFunnel: "mouthFunnel",
    mouthPucker: "mouthPucker",
    mouthSmileLeft: "mouthSmileLeft",
    mouthSmileRight: "mouthSmileRight",
    eyeBlinkLeft: "eyeBlinkLeft",
    eyeBlinkRight: "eyeBlinkRight",
    browInnerUp: "browInnerUp",
  };

  // Oculus visemes, if the model ships them. Better lip-sync than raw
  // amplitude, used only when the mesh actually has them.
  const VISEMES = [
    "viseme_sil", "viseme_PP", "viseme_FF", "viseme_TH", "viseme_DD",
    "viseme_kk", "viseme_CH", "viseme_SS", "viseme_nn", "viseme_RR",
    "viseme_aa", "viseme_E", "viseme_I", "viseme_O", "viseme_U",
  ];

  const AGENTS_3D = {
    putri: {
      name: "Putri", role: "CEO",
      model: null,                    // static/avatars/putri/putri.glb
      accent: "#ff8fb8",
      camera: { y: 1.55, z: 0.72, fov: 28 },
      voice: { provider: "openai", voice: "shimmer", lang: "ms-MY" },
    },
    alisya: {
      name: "Alisya", role: "CTO", model: null, accent: "#5fb3ff",
      camera: { y: 1.55, z: 0.72, fov: 28 },
      voice: { provider: "openai", voice: "nova", lang: "ms-MY" },
    },
    julia: {
      name: "Julia", role: "CFO", model: null, accent: "#ffc857",
      camera: { y: 1.55, z: 0.72, fov: 28 },
      voice: { provider: "openai", voice: "sage", lang: "ms-MY" },
    },
    farah: {
      name: "Farah", role: "CMO", model: null, accent: "#ff7a8a",
      camera: { y: 1.55, z: 0.72, fov: 28 },
      voice: { provider: "openai", voice: "coral", lang: "ms-MY" },
    },
    delisha: {
      name: "Delisha", role: "COO", model: null, accent: "#6ee7b7",
      camera: { y: 1.55, z: 0.72, fov: 28 },
      voice: { provider: "openai", voice: "alloy", lang: "ms-MY" },
    },
  };

  // How a desk state maps to what the avatar does. Kept here rather
  // than in the renderer so a new state is a data change too.
  const STATE_BEHAVIOUR = {
    idle:     { clip: "idle",     blink: true,  sway: 0.15 },
    thinking: { clip: "thinking", blink: true,  sway: 0.35, brow: 0.4 },
    working:  { clip: "idle",     blink: true,  sway: 0.5 },
    done:     { clip: "idle",     blink: true,  sway: 0.2, smile: 0.5 },
    error:    { clip: "idle",     blink: true,  sway: 0.1, brow: 0.7 },
    offline:  { clip: null,       blink: false, sway: 0 },
  };

  window.SAGAX_3D = { AGENTS_3D, STATE_BEHAVIOUR, ARKIT, VISEMES };
})();
