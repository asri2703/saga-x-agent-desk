/* ============================================================
   Saga X — Anime Avatar SVG library
   5 distinct female characters, Ghibli-inspired, inline SVG
   ============================================================
   Each avatar is returned as a string and injected into the DOM.
   Color schemes are tuned per role; hair and outfits differ.
   Body parts are grouped so CSS animations look natural.
*/

const AVATARS = {

  /* ────────────────────────────────────────────────────────────
     PUTRI — CEO
     Long pink-blonde hair, soft lavender eyes, blazer
     Calm, composed leader presence
  ──────────────────────────────────────────────────────────── */
  putri: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Putri, CEO">
  <defs>
    <linearGradient id="putri-hair" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffe1c4"/>
      <stop offset="50%" stop-color="#ffc7d8"/>
      <stop offset="100%" stop-color="#ffb0c8"/>
    </linearGradient>
    <radialGradient id="putri-skin" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ffe9dc"/>
      <stop offset="100%" stop-color="#f9d4bd"/>
    </radialGradient>
    <linearGradient id="putri-blazer" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#7a5cff"/>
      <stop offset="100%" stop-color="#5236c4"/>
    </linearGradient>
  </defs>

  <!-- back hair -->
  <path d="M30,80 Q20,55 35,38 Q50,18 75,18 Q100,18 115,38 Q130,55 120,80 L118,110 Q105,98 100,90 Q98,80 95,72 L90,95 L40,95 L35,72 Q32,80 30,90 Q25,98 12,110 Z"
        fill="url(#putri-hair)"/>

  <!-- neck -->
  <rect x="55" y="92" width="20" height="14" rx="4" fill="url(#putri-skin)"/>

  <!-- shoulders / blazer -->
  <path d="M28,160 L28,130 Q35,108 65,108 Q95,108 102,130 L102,160 Z" fill="url(#putri-blazer)"/>
  <!-- shirt collar -->
  <path d="M55,108 L65,124 L75,108 L70,114 L65,118 L60,114 Z" fill="#f7f1ff"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="26" ry="30" fill="url(#putri-skin)"/>

  <!-- front hair bangs (CEO soft side-swept) -->
  <path d="M40,40 Q42,28 55,28 Q60,40 60,52 Q56,44 48,42 Q44,52 40,50 Z" fill="url(#putri-hair)"/>
  <path d="M90,40 Q88,28 75,28 Q70,40 70,52 Q74,44 82,42 Q86,52 90,50 Z" fill="url(#putri-hair)"/>
  <!-- center hair swoop -->
  <path d="M55,30 Q65,22 75,30 Q72,38 65,38 Q58,38 55,30 Z" fill="url(#putri-hair)"/>

  <!-- hair strands beside face -->
  <path d="M40,55 Q38,80 45,95 L40,95 Q35,80 38,55 Z" fill="url(#putri-hair)"/>
  <path d="M90,55 Q92,80 85,95 L90,95 Q95,80 92,55 Z" fill="url(#putri-hair)"/>

  <!-- eyes (large anime) -->
  <g class="eyes">
    <ellipse cx="55" cy="65" rx="3.6" ry="5" fill="#5a3a8a"/>
    <ellipse cx="75" cy="65" rx="3.6" ry="5" fill="#5a3a8a"/>
    <ellipse cx="55.6" cy="63.5" rx="1" ry="1.5" fill="#fff"/>
    <ellipse cx="75.6" cy="63.5" rx="1" ry="1.5" fill="#fff"/>
  </g>

  <!-- brows -->
  <path d="M50,58 Q55,56 60,58" stroke="#c98ba8" stroke-width="1.2" fill="none" stroke-linecap="round"/>
  <path d="M70,58 Q75,56 80,58" stroke="#c98ba8" stroke-width="1.2" fill="none" stroke-linecap="round"/>

  <!-- blush -->
  <ellipse cx="48" cy="72" rx="3.5" ry="2" fill="#ffb0c8" opacity="0.55"/>
  <ellipse cx="82" cy="72" rx="3.5" ry="2" fill="#ffb0c8" opacity="0.55"/>

  <!-- mouth (small smile) -->
  <path d="M60,76 Q65,79 70,76" stroke="#a85770" stroke-width="1.4" fill="none" stroke-linecap="round"/>

  <!-- CEO badge on blazer -->
  <circle cx="42" cy="138" r="4" fill="#ffd966" stroke="#b88a1f" stroke-width="0.6"/>
</svg>

<!-- thought bubble for thinking state -->
<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(255,255,255,0.92)"/>
  <text x="22" y="15" text-anchor="middle" font-size="14" font-weight="700" fill="#7a5cff">?</text>
  <circle cx="11" cy="22" r="2.5" fill="rgba(255,255,255,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(255,255,255,0.85)"/>
</svg>
`,

  /* ────────────────────────────────────────────────────────────
     ALISYA — CTO
     Short navy hair, glasses, headset, hoodie under blazer
  ──────────────────────────────────────────────────────────── */
  alisya: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Alisya, CTO">
  <defs>
    <linearGradient id="alisya-hair" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#3a4d6e"/>
      <stop offset="100%" stop-color="#1f2d48"/>
    </linearGradient>
    <radialGradient id="alisya-skin" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#fff0e1"/>
      <stop offset="100%" stop-color="#f5d4b4"/>
    </radialGradient>
    <linearGradient id="alisya-hoodie" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#5fb3ff"/>
      <stop offset="100%" stop-color="#2a7bd6"/>
    </linearGradient>
  </defs>

  <!-- back hair (short bob) -->
  <path d="M38,68 Q32,40 50,30 Q65,22 80,30 Q98,40 92,68 L92,82 Q86,72 82,68 L82,80 L48,80 L48,68 Q44,72 38,82 Z"
        fill="url(#alisya-hair)"/>

  <!-- neck -->
  <rect x="56" y="92" width="18" height="14" rx="4" fill="url(#alisya-skin)"/>

  <!-- hoodie + shoulders -->
  <path d="M22,160 L22,134 Q30,110 65,110 Q100,110 108,134 L108,160 Z" fill="url(#alisya-hoodie)"/>
  <!-- hoodie strings -->
  <line x1="60" y1="115" x2="58" y2="135" stroke="#fff" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>
  <line x1="70" y1="115" x2="72" y2="135" stroke="#fff" stroke-width="1.5" stroke-linecap="round" opacity="0.7"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#alisya-skin)"/>

  <!-- front bangs (sharp, technical) -->
  <path d="M40,42 Q42,30 55,30 Q58,42 56,52 L48,48 Q42,46 40,42 Z" fill="url(#alisya-hair)"/>
  <path d="M90,42 Q88,30 75,30 Q72,42 74,52 L82,48 Q88,46 90,42 Z" fill="url(#alisya-hair)"/>
  <path d="M55,32 Q65,26 75,32 Q70,40 65,38 Q60,40 55,32 Z" fill="url(#alisya-hair)"/>

  <!-- side hair -->
  <path d="M40,55 L40,80 L46,75 L46,55 Z" fill="url(#alisya-hair)"/>
  <path d="M90,55 L90,80 L84,75 L84,55 Z" fill="url(#alisya-hair)"/>

  <!-- GLASSES -->
  <g stroke="#1f2d48" stroke-width="1.5" fill="none">
    <circle cx="55" cy="65" r="7" fill="rgba(180,220,255,0.25)"/>
    <circle cx="75" cy="65" r="7" fill="rgba(180,220,255,0.25)"/>
    <line x1="62" y1="65" x2="68" y2="65"/>
  </g>

  <!-- eyes (focused, behind glasses) -->
  <g class="eyes">
    <ellipse cx="55" cy="65" rx="2.4" ry="3.2" fill="#1f2d48"/>
    <ellipse cx="75" cy="65" rx="2.4" ry="3.2" fill="#1f2d48"/>
  </g>

  <!-- brows (determined) -->
  <path d="M50,55 L60,57" stroke="#1f2d48" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M70,57 L80,55" stroke="#1f2d48" stroke-width="1.4" stroke-linecap="round"/>

  <!-- blush -->
  <ellipse cx="48" cy="73" rx="3" ry="1.6" fill="#ffb0c8" opacity="0.45"/>
  <ellipse cx="82" cy="73" rx="3" ry="1.6" fill="#ffb0c8" opacity="0.45"/>

  <!-- mouth (small confident smirk) -->
  <path d="M60,76 L70,76" stroke="#7a4458" stroke-width="1.4" stroke-linecap="round"/>

  <!-- HEADSET -->
  <path d="M40,55 Q65,30 90,55" stroke="#1f2d48" stroke-width="2" fill="none"/>
  <ellipse cx="38" cy="64" rx="4" ry="6" fill="#1f2d48"/>
  <ellipse cx="92" cy="64" rx="4" ry="6" fill="#1f2d48"/>

  <!-- CTO code badge -->
  <rect x="38" y="135" width="10" height="10" rx="2" fill="#0d2238" stroke="#5fb3ff" stroke-width="0.8"/>
  <text x="43" y="143" text-anchor="middle" font-size="8" fill="#5fb3ff" font-family="monospace" font-weight="700">&lt;/&gt;</text>
</svg>

<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(95,179,255,0.92)"/>
  <text x="22" y="15" text-anchor="middle" font-size="11" font-weight="700" fill="#fff" font-family="monospace">{ }</text>
  <circle cx="11" cy="22" r="2.5" fill="rgba(95,179,255,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(95,179,255,0.85)"/>
</svg>
`,

  /* ────────────────────────────────────────────────────────────
     JULIA — CFO
     Auburn hair in low bun, gold earrings, blazer with brooch
  ──────────────────────────────────────────────────────────── */
  julia: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Julia, CFO">
  <defs>
    <linearGradient id="julia-hair" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a85a2a"/>
      <stop offset="100%" stop-color="#6e3a18"/>
    </linearGradient>
    <radialGradient id="julia-skin" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ffe9d9"/>
      <stop offset="100%" stop-color="#f6cda9"/>
    </radialGradient>
    <linearGradient id="julia-blazer" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#d68a3a"/>
      <stop offset="100%" stop-color="#8a5a1c"/>
    </linearGradient>
  </defs>

  <!-- hair back with bun -->
  <path d="M40,70 Q34,45 50,32 Q65,24 80,32 Q96,45 90,70 L88,82 Q82,72 78,68 L78,80 L52,80 L52,68 Q48,72 42,82 Z"
        fill="url(#julia-hair)"/>
  <!-- bun on top -->
  <ellipse cx="65" cy="24" rx="12" ry="9" fill="url(#julia-hair)"/>
  <ellipse cx="65" cy="22" rx="10" ry="7" fill="#8a4d22" opacity="0.6"/>

  <!-- neck -->
  <rect x="56" y="92" width="18" height="14" rx="4" fill="url(#julia-skin)"/>

  <!-- blazer + shoulders -->
  <path d="M26,160 L26,132 Q34,108 65,108 Q96,108 104,132 L104,160 Z" fill="url(#julia-blazer)"/>
  <!-- blouse under -->
  <path d="M55,108 L65,128 L75,108 L70,116 L65,120 L60,116 Z" fill="#fff4dc"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#julia-skin)"/>

  <!-- bangs (swept, mature) -->
  <path d="M42,44 Q44,32 56,32 Q60,42 58,52 L48,46 Q42,46 42,44 Z" fill="url(#julia-hair)"/>
  <path d="M88,44 Q86,32 74,32 Q70,42 72,52 L82,46 Q88,46 88,44 Z" fill="url(#julia-hair)"/>

  <!-- side hair -->
  <path d="M42,52 L42,76 L48,72 L48,52 Z" fill="url(#julia-hair)"/>
  <path d="M88,52 L88,76 L82,72 L82,52 Z" fill="url(#julia-hair)"/>

  <!-- gold earrings -->
  <circle cx="41" cy="68" r="1.6" fill="#ffd966"/>
  <circle cx="89" cy="68" r="1.6" fill="#ffd966"/>

  <!-- eyes (warm amber, business-like) -->
  <g class="eyes">
    <ellipse cx="55" cy="66" rx="3.2" ry="4.2" fill="#7a4a18"/>
    <ellipse cx="75" cy="66" rx="3.2" ry="4.2" fill="#7a4a18"/>
    <ellipse cx="55.6" cy="65" rx="0.9" ry="1.2" fill="#fff"/>
    <ellipse cx="75.6" cy="65" rx="0.9" ry="1.2" fill="#fff"/>
  </g>

  <!-- brows (polished arch) -->
  <path d="M50,59 Q55,57 60,59" stroke="#5a3a18" stroke-width="1.2" fill="none" stroke-linecap="round"/>
  <path d="M70,59 Q75,57 80,59" stroke="#5a3a18" stroke-width="1.2" fill="none" stroke-linecap="round"/>

  <!-- blush -->
  <ellipse cx="48" cy="73" rx="3" ry="1.6" fill="#e89a8a" opacity="0.45"/>
  <ellipse cx="82" cy="73" rx="3" ry="1.6" fill="#e89a8a" opacity="0.45"/>

  <!-- mouth (closed professional smile) -->
  <path d="M58,76 Q65,79 72,76" stroke="#7a3838" stroke-width="1.4" fill="none" stroke-linecap="round"/>

  <!-- CFO brooch (coin / dollar) -->
  <circle cx="44" cy="138" r="4.5" fill="#ffd966" stroke="#b88a1f" stroke-width="0.6"/>
  <text x="44" y="141" text-anchor="middle" font-size="6" fill="#7a5a18" font-weight="700">$</text>
</svg>

<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(255,217,102,0.95)"/>
  <text x="22" y="15" text-anchor="middle" font-size="13" font-weight="700" fill="#7a5a18">$</text>
  <circle cx="11" cy="22" r="2.5" fill="rgba(255,217,102,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(255,217,102,0.85)"/>
</svg>
`,

  /* ────────────────────────────────────────────────────────────
     FARAH — CMO
     Curly red-coral hair, magenta scarf, expressive eyes
  ──────────────────────────────────────────────────────────── */
  farah: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Farah, CMO">
  <defs>
    <linearGradient id="farah-hair" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ff7a5a"/>
      <stop offset="100%" stop-color="#c44030"/>
    </linearGradient>
    <radialGradient id="farah-skin" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ffe1cc"/>
      <stop offset="100%" stop-color="#f5c4a8"/>
    </radialGradient>
    <linearGradient id="farah-top" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#e91e63"/>
      <stop offset="100%" stop-color="#a31844"/>
    </linearGradient>
  </defs>

  <!-- curly back hair (voluminous) -->
  <g fill="url(#farah-hair)">
    <circle cx="38" cy="50" r="11"/>
    <circle cx="92" cy="50" r="11"/>
    <circle cx="30" cy="65" r="10"/>
    <circle cx="100" cy="65" r="10"/>
    <circle cx="35" cy="80" r="9"/>
    <circle cx="95" cy="80" r="9"/>
    <ellipse cx="65" cy="92" rx="32" ry="14"/>
  </g>

  <!-- neck -->
  <rect x="56" y="94" width="18" height="12" rx="3" fill="url(#farah-skin)"/>

  <!-- magenta top / scarf -->
  <path d="M28,160 L28,128 Q36,108 65,108 Q94,108 102,128 L102,160 Z" fill="url(#farah-top)"/>
  <!-- scarf detail -->
  <path d="M48,108 Q52,118 56,108 Q60,116 64,108 Q68,116 72,108 Q76,118 80,108 L80,124 L48,124 Z"
        fill="#ffd1e0" opacity="0.7"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#farah-skin)"/>

  <!-- curly bangs (bouncy) -->
  <g fill="url(#farah-hair)">
    <circle cx="48" cy="40" r="8"/>
    <circle cx="58" cy="34" r="9"/>
    <circle cx="68" cy="32" r="10"/>
    <circle cx="78" cy="36" r="8"/>
    <circle cx="44" cy="48" r="6"/>
    <circle cx="82" cy="48" r="6"/>
  </g>

  <!-- side curls -->
  <circle cx="40" cy="58" r="6" fill="url(#farah-hair)"/>
  <circle cx="90" cy="58" r="6" fill="url(#farah-hair)"/>

  <!-- bright expressive eyes -->
  <g class="eyes">
    <ellipse cx="55" cy="65" rx="4" ry="5.2" fill="#2a8a6e"/>
    <ellipse cx="75" cy="65" rx="4" ry="5.2" fill="#2a8a6e"/>
    <ellipse cx="55.8" cy="63" rx="1.3" ry="1.8" fill="#fff"/>
    <ellipse cx="75.8" cy="63" rx="1.3" ry="1.8" fill="#fff"/>
  </g>

  <!-- eyelashes (lashes) -->
  <path d="M50,60 L52,58" stroke="#7a2a18" stroke-width="1.2" stroke-linecap="round"/>
  <path d="M55,58 L57,56" stroke="#7a2a18" stroke-width="1.2" stroke-linecap="round"/>
  <path d="M73,56 L75,58" stroke="#7a2a18" stroke-width="1.2" stroke-linecap="round"/>
  <path d="M78,58 L80,60" stroke="#7a2a18" stroke-width="1.2" stroke-linecap="round"/>

  <!-- brows (arched, expressive) -->
  <path d="M50,55 Q55,52 60,55" stroke="#a43020" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M70,55 Q75,52 80,55" stroke="#a43020" stroke-width="1.3" fill="none" stroke-linecap="round"/>

  <!-- blush (more pink for energy) -->
  <ellipse cx="48" cy="73" rx="3.5" ry="2" fill="#ff8095" opacity="0.65"/>
  <ellipse cx="82" cy="73" rx="3.5" ry="2" fill="#ff8095" opacity="0.65"/>

  <!-- mouth (slight smile) -->
  <path d="M58,76 Q65,80 72,76" stroke="#a83040" stroke-width="1.5" fill="none" stroke-linecap="round"/>

  <!-- CMO creative badge (star) -->
  <path d="M44,134 L46,138 L50,138 L47,141 L48,145 L44,143 L40,145 L41,141 L38,138 L42,138 Z"
        fill="#ffd966" stroke="#b88a1f" stroke-width="0.5"/>
</svg>

<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(233,30,99,0.92)"/>
  <path d="M22,5 L24,9 L28,9 L25,12 L26,16 L22,14 L18,16 L19,12 L16,9 L20,9 Z"
        transform="translate(0,0) scale(0.6) translate(15,5)" fill="#fff"/>
  <circle cx="11" cy="22" r="2.5" fill="rgba(233,30,99,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(233,30,99,0.85)"/>
</svg>
`,

  /* ────────────────────────────────────────────────────────────
     DELISHA — COO
     Mint-green ponytail, clipboard, organized look
  ──────────────────────────────────────────────────────────── */
  delisha: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Delisha, COO">
  <defs>
    <linearGradient id="delisha-hair" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#5fe0b8"/>
      <stop offset="100%" stop-color="#2a9e76"/>
    </linearGradient>
    <radialGradient id="delisha-skin" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ffe2cf"/>
      <stop offset="100%" stop-color="#f6c8a8"/>
    </radialGradient>
    <linearGradient id="delisha-shirt" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#6ee7b7"/>
      <stop offset="100%" stop-color="#2fa97a"/>
    </linearGradient>
  </defs>

  <!-- ponytail (back, swept right) -->
  <path d="M85,42 Q110,50 108,80 Q106,100 100,108 Q98,98 96,90 Q92,82 88,75 Z" fill="url(#delisha-hair)"/>
  <ellipse cx="103" cy="90" rx="6" ry="14" fill="url(#delisha-hair)"/>

  <!-- main hair back -->
  <path d="M40,68 Q34,42 52,30 Q65,24 78,30 Q96,42 90,68 L88,82 Q84,72 80,68 L80,80 L50,80 L50,68 Q46,72 42,82 Z"
        fill="url(#delisha-hair)"/>

  <!-- neck -->
  <rect x="56" y="92" width="18" height="14" rx="4" fill="url(#delisha-skin)"/>

  <!-- shirt + shoulders -->
  <path d="M26,160 L26,134 Q34,108 65,108 Q96,108 104,134 L104,160 Z" fill="url(#delisha-shirt)"/>
  <!-- collar V -->
  <path d="M55,108 L65,124 L75,108 L70,116 L65,120 L60,116 Z" fill="#fff4ec"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#delisha-skin)"/>

  <!-- asymmetric bangs (side-swept) -->
  <path d="M40,44 Q44,30 60,30 Q66,38 64,52 L52,46 Q42,46 40,44 Z" fill="url(#delisha-hair)"/>
  <path d="M70,40 Q72,32 82,30 Q90,32 90,42 Q86,46 78,46 Q72,46 70,40 Z" fill="url(#delisha-hair)"/>

  <!-- side hair -->
  <path d="M40,52 L40,76 L46,72 L46,52 Z" fill="url(#delisha-hair)"/>
  <path d="M88,52 L88,76 L82,72 L82,52 Z" fill="url(#delisha-hair)"/>

  <!-- hair tie detail -->
  <ellipse cx="100" cy="50" rx="5" ry="4" fill="#ffd966"/>

  <!-- eyes (bright green) -->
  <g class="eyes">
    <ellipse cx="55" cy="66" rx="3.4" ry="4.4" fill="#3a8a5a"/>
    <ellipse cx="75" cy="66" rx="3.4" ry="4.4" fill="#3a8a5a"/>
    <ellipse cx="55.7" cy="64.5" rx="1" ry="1.4" fill="#fff"/>
    <ellipse cx="75.7" cy="64.5" rx="1" ry="1.4" fill="#fff"/>
  </g>

  <!-- brows (focused, organized) -->
  <path d="M50,59 Q55,57 60,59" stroke="#2a6e4a" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M70,59 Q75,57 80,59" stroke="#2a6e4a" stroke-width="1.3" fill="none" stroke-linecap="round"/>

  <!-- blush -->
  <ellipse cx="48" cy="74" rx="3" ry="1.8" fill="#ff9eaa" opacity="0.5"/>
  <ellipse cx="82" cy="74" rx="3" ry="1.8" fill="#ff9eaa" opacity="0.5"/>

  <!-- mouth (gentle smile) -->
  <path d="M58,77 Q65,80 72,77" stroke="#9a3a4a" stroke-width="1.4" fill="none" stroke-linecap="round"/>

  <!-- clipboard badge -->
  <rect x="38" y="132" width="14" height="18" rx="1" fill="#fff4ec" stroke="#2a6e4a" stroke-width="0.8"/>
  <rect x="42" y="130" width="6" height="3" rx="0.5" fill="#2a6e4a"/>
  <line x1="40" y1="138" x2="50" y2="138" stroke="#2a6e4a" stroke-width="0.6"/>
  <line x1="40" y1="142" x2="50" y2="142" stroke="#2a6e4a" stroke-width="0.6"/>
  <line x1="40" y1="146" x2="48" y2="146" stroke="#2a6e4a" stroke-width="0.6"/>
</svg>

<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(110,231,183,0.95)"/>
  <path d="M16,11 L21,15 L28,8" stroke="#2a6e4a" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="11" cy="22" r="2.5" fill="rgba(110,231,183,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(110,231,183,0.85)"/>
</svg>
`,
};

// Helper: render avatar by id
function renderAvatar(id) {
  if (!AVATARS[id]) {
    return `<div class="avatar-svg" style="display:flex;align-items:center;justify-content:center;color:#888">?</div>`;
  }
  return AVATARS[id]() +
    `<div class="typing-dots"><span></span><span></span><span></span></div>`;
}

window.AVATARS = AVATARS;
window.renderAvatar = renderAvatar;
