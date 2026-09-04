/* ============================================================
   Saga X — 3D-Style Portrait SVG library
   Photoreal-looking female characters using SVG gradients,
   soft shadows, and depth cues. No AI/raster needed.
   ============================================================
   Design principles:
   - Single light source: top-left → bottom-right shadow falloff
   - Skin: multi-stop radial gradients + cheek highlights
   - Hair: layered curves with depth gradient + specular highlight
   - Eyes: layered ellipses with pupil, iris, catchlight
   - Body: fabric folds suggested via gradient stops
   - All animatable: CSS animations on container move everything
*/

const AVATARS = {

  /* ────────────────────────────────────────────────────────────
     PUTRI — CEO
     Long honey-blonde hair, hazel eyes, executive blazer
     Tone: composed, warm, leadership
  ──────────────────────────────────────────────────────────── */
  putri: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Putri, CEO">
  <defs>
    <!-- Skin: warm peach with cheek blush -->
    <radialGradient id="putri-skin" cx="35%" cy="35%" r="75%">
      <stop offset="0%" stop-color="#fff0e3"/>
      <stop offset="40%" stop-color="#fcd9bd"/>
      <stop offset="80%" stop-color="#e8b594"/>
      <stop offset="100%" stop-color="#b8835c"/>
    </radialGradient>
    <!-- Cheek blush overlay -->
    <radialGradient id="putri-cheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ff9a8a" stop-opacity="0.55"/>
      <stop offset="60%" stop-color="#ff9a8a" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#ff9a8a" stop-opacity="0"/>
    </radialGradient>
    <!-- Hair main: honey blonde with depth -->
    <linearGradient id="putri-hair" x1="30%" y1="0%" x2="70%" y2="100%">
      <stop offset="0%" stop-color="#fde8b6"/>
      <stop offset="40%" stop-color="#e8c278"/>
      <stop offset="80%" stop-color="#a87838"/>
      <stop offset="100%" stop-color="#6e4a1f"/>
    </linearGradient>
    <!-- Hair shine highlight -->
    <linearGradient id="putri-shine" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fff8d6" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#fff8d6" stop-opacity="0"/>
    </linearGradient>
    <!-- Blazer: deep aubergine -->
    <linearGradient id="putri-blazer" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#5a3275"/>
      <stop offset="60%" stop-color="#3a1e54"/>
      <stop offset="100%" stop-color="#1f0e36"/>
    </linearGradient>
    <!-- Shirt collar: pearl white -->
    <linearGradient id="putri-shirt" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#d9d3e8"/>
    </linearGradient>
    <!-- Eye iris -->
    <radialGradient id="putri-eye" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#8fbf7c"/>
      <stop offset="60%" stop-color="#3a6e2e"/>
      <stop offset="100%" stop-color="#1a3d12"/>
    </radialGradient>
    <!-- Nose shadow gradient -->
    <linearGradient id="putri-nose-shadow" x1="50%" y1="0%" x2="50%" y2="100%">
      <stop offset="0%" stop-color="#9c6e4d" stop-opacity="0"/>
      <stop offset="100%" stop-color="#7a4d2e" stop-opacity="0.5"/>
    </linearGradient>
    <!-- Drop shadow under chin -->
    <radialGradient id="putri-chin-shadow" cx="50%" cy="0%" r="60%">
      <stop offset="0%" stop-color="#5e3520" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#5e3520" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- back hair (long, behind shoulders) -->
  <path d="M22,90 Q12,55 35,28 Q55,12 75,14 Q105,18 118,45 Q124,72 116,98 L116,128 Q108,118 102,108 Q98,98 95,90 L92,118 L40,118 L36,90 Q32,98 28,108 Q22,118 14,128 L14,98 Z"
        fill="url(#putri-hair)"/>
  <!-- hair shine overlay -->
  <path d="M40,30 Q55,18 75,20 Q92,28 100,42 Q88,32 72,30 Q54,30 40,42 Z"
        fill="url(#putri-shine)" opacity="0.7"/>

  <!-- neck -->
  <path d="M52,98 L52,116 Q65,124 78,116 L78,98 Z" fill="url(#putri-skin)"/>
  <!-- chin shadow under jaw -->
  <ellipse cx="65" cy="106" rx="20" ry="6" fill="url(#putri-chin-shadow)"/>

  <!-- shoulders / blazer -->
  <path d="M22,160 L22,128 Q34,108 65,108 Q96,108 108,128 L108,160 Z" fill="url(#putri-blazer)"/>
  <!-- lapel shadow left -->
  <path d="M22,160 L22,128 Q34,108 50,108 L48,160 Z" fill="#000" opacity="0.15"/>
  <!-- lapel shadow right -->
  <path d="M108,160 L108,128 Q96,108 80,108 L82,160 Z" fill="#000" opacity="0.15"/>
  <!-- shirt collar V -->
  <path d="M52,108 L65,128 L78,108 L72,116 L65,120 L58,116 Z" fill="url(#putri-shirt)"/>
  <!-- collar shadow -->
  <path d="M52,108 L58,116 L65,120 L72,116 L78,108 L70,118 L65,124 L60,118 Z" fill="#000" opacity="0.1"/>

  <!-- FACE -->
  <ellipse cx="65" cy="62" rx="26" ry="30" fill="url(#putri-skin)"/>

  <!-- face highlight (top-left light) -->
  <ellipse cx="50" cy="48" rx="12" ry="14" fill="#fff" opacity="0.18"/>

  <!-- front hair bangs (swept) -->
  <path d="M40,40 Q42,28 56,28 Q60,40 58,52 L48,46 Q42,46 40,42 Z" fill="url(#putri-hair)"/>
  <path d="M90,40 Q88,28 74,28 Q70,40 72,52 L82,46 Q88,46 90,42 Z" fill="url(#putri-hair)"/>
  <path d="M55,28 Q65,22 75,28 Q72,38 65,38 Q58,38 55,28 Z" fill="url(#putri-hair)"/>

  <!-- side hair strands -->
  <path d="M40,55 Q36,80 44,98 L40,98 Q34,80 38,55 Z" fill="url(#putri-hair)"/>
  <path d="M90,55 Q94,80 86,98 L90,98 Q96,80 92,55 Z" fill="url(#putri-hair)"/>

  <!-- nose (subtle) -->
  <path d="M62,68 Q63,76 65,78 Q67,76 68,68 Q66,72 65,72 Q64,72 62,68 Z" fill="url(#putri-nose-shadow)" opacity="0.6"/>
  <path d="M65,72 Q65,75 64,76" stroke="#a87a55" stroke-width="0.5" fill="none" opacity="0.5"/>

  <!-- EYEBROWS (3D-looking, layered) -->
  <path d="M48,57 Q55,53 62,57 Q55,55 48,57 Z" fill="#6e4a1f"/>
  <path d="M68,57 Q75,53 82,57 Q75,55 68,57 Z" fill="#6e4a1f"/>

  <!-- EYES (photoreal layered) -->
  <g>
    <!-- eye white with shadow underneath -->
    <ellipse cx="55" cy="66" rx="4.5" ry="3" fill="#fbfaf6"/>
    <ellipse cx="75" cy="66" rx="4.5" ry="3" fill="#fbfaf6"/>
    <!-- upper eyelid line -->
    <path d="M50.5,65 Q55,62 59.5,65" stroke="#3a2415" stroke-width="1.4" fill="none" stroke-linecap="round"/>
    <path d="M70.5,65 Q75,62 79.5,65" stroke="#3a2415" stroke-width="1.4" fill="none" stroke-linecap="round"/>
    <!-- iris -->
    <ellipse cx="55" cy="66" rx="2.8" ry="2.8" fill="url(#putri-eye)"/>
    <ellipse cx="75" cy="66" rx="2.8" ry="2.8" fill="url(#putri-eye)"/>
    <!-- pupil -->
    <ellipse cx="55" cy="66" rx="1.2" ry="1.2" fill="#0a0a0a"/>
    <ellipse cx="75" cy="66" rx="1.2" ry="1.2" fill="#0a0a0a"/>
    <!-- catchlight (specular highlight) -->
    <ellipse cx="56" cy="65" rx="0.8" ry="0.8" fill="#fff"/>
    <ellipse cx="76" cy="65" rx="0.8" ry="0.8" fill="#fff"/>
    <!-- subtle lash -->
    <path d="M51,64 L52.5,62.5" stroke="#3a2415" stroke-width="0.5" stroke-linecap="round"/>
    <path d="M71,64 L72.5,62.5" stroke="#3a2415" stroke-width="0.5" stroke-linecap="round"/>
  </g>

  <!-- cheeks -->
  <ellipse cx="46" cy="74" rx="5" ry="3.5" fill="url(#putri-cheek)"/>
  <ellipse cx="84" cy="74" rx="5" ry="3.5" fill="url(#putri-cheek)"/>

  <!-- mouth (closed, soft) -->
  <path d="M58,79 Q65,82 72,79" stroke="#a85a55" stroke-width="1.6" fill="none" stroke-linecap="round"/>
  <!-- lower lip highlight -->
  <path d="M60,80 Q65,82 70,80" stroke="#d4756e" stroke-width="0.6" fill="none" opacity="0.6"/>

  <!-- earring (subtle gold dot) -->
  <circle cx="39" cy="70" r="0.8" fill="#f4cf6a"/>
  <circle cx="91" cy="70" r="0.8" fill="#f4cf6a"/>

  <!-- CEO badge pin on blazer -->
  <circle cx="42" cy="138" r="3.5" fill="#e8c450" stroke="#9a7a1c" stroke-width="0.5"/>
  <circle cx="42" cy="138" r="2" fill="#9a7a1c"/>
</svg>

<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(255,255,255,0.95)"/>
  <text x="22" y="15" text-anchor="middle" font-size="13" font-weight="700" fill="#5a3275">?</text>
  <circle cx="11" cy="22" r="2.5" fill="rgba(255,255,255,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(255,255,255,0.85)"/>
</svg>
`,

  /* ────────────────────────────────────────────────────────────
     ALISYA — CTO
     Short dark-brown bob, sharp features, smart watch visible
     Tone: focused, technical, modern
  ──────────────────────────────────────────────────────────── */
  alisya: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Alisya, CTO">
  <defs>
    <radialGradient id="alisya-skin" cx="35%" cy="35%" r="75%">
      <stop offset="0%" stop-color="#fae0c8"/>
      <stop offset="40%" stop-color="#f0c5a0"/>
      <stop offset="80%" stop-color="#cf9670"/>
      <stop offset="100%" stop-color="#8d5e3a"/>
    </radialGradient>
    <radialGradient id="alisya-cheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#e88a7c" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#e88a7c" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="alisya-hair" x1="30%" y1="0%" x2="70%" y2="100%">
      <stop offset="0%" stop-color="#5a3520"/>
      <stop offset="50%" stop-color="#3a2010"/>
      <stop offset="100%" stop-color="#1a0c05"/>
    </linearGradient>
    <linearGradient id="alisya-shine" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a87850" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#a87850" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="alisya-hoodie" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#5fb3ff"/>
      <stop offset="60%" stop-color="#2a7bd6"/>
      <stop offset="100%" stop-color="#0d3a72"/>
    </linearGradient>
    <radialGradient id="alisya-eye" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#6e4a30"/>
      <stop offset="100%" stop-color="#2a1810"/>
    </radialGradient>
  </defs>

  <!-- back hair (short bob) -->
  <path d="M38,68 Q32,40 50,28 Q65,22 80,28 Q98,40 92,68 L92,82 Q86,72 82,68 L82,80 L48,80 L48,68 Q44,72 38,82 Z"
        fill="url(#alisya-hair)"/>
  <path d="M48,30 Q65,26 82,30 Q70,24 65,24 Q60,24 48,30 Z" fill="url(#alisya-shine)"/>

  <!-- neck -->
  <path d="M53,98 L53,116 Q65,122 77,116 L77,98 Z" fill="url(#alisya-skin)"/>
  <ellipse cx="65" cy="106" rx="20" ry="5" fill="#000" opacity="0.2"/>

  <!-- hoodie -->
  <path d="M22,160 L22,134 Q30,110 65,110 Q100,110 108,134 L108,160 Z" fill="url(#alisya-hoodie)"/>
  <path d="M22,160 L22,134 Q30,110 50,110 L48,160 Z" fill="#000" opacity="0.15"/>
  <!-- hoodie strings -->
  <line x1="60" y1="115" x2="58" y2="135" stroke="#fff" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
  <line x1="70" y1="115" x2="72" y2="135" stroke="#fff" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
  <!-- string tips -->
  <circle cx="58" cy="135" r="1.5" fill="#fff" opacity="0.7"/>
  <circle cx="72" cy="135" r="1.5" fill="#fff" opacity="0.7"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#alisya-skin)"/>
  <ellipse cx="50" cy="48" rx="11" ry="13" fill="#fff" opacity="0.18"/>

  <!-- bangs (sharp, technical) -->
  <path d="M40,42 Q42,30 55,30 Q58,42 56,52 L48,48 Q42,46 40,42 Z" fill="url(#alisya-hair)"/>
  <path d="M90,42 Q88,30 75,30 Q72,42 74,52 L82,48 Q88,46 90,42 Z" fill="url(#alisya-hair)"/>
  <path d="M55,32 Q65,26 75,32 Q70,40 65,38 Q60,40 55,32 Z" fill="url(#alisya-hair)"/>

  <!-- side hair -->
  <path d="M40,55 L40,80 L46,75 L46,55 Z" fill="url(#alisya-hair)"/>
  <path d="M90,55 L90,80 L84,75 L84,55 Z" fill="url(#alisya-hair)"/>

  <!-- GLASSES -->
  <g stroke="#1f2d48" stroke-width="1.4" fill="none">
    <circle cx="55" cy="65" r="7" fill="rgba(180,220,255,0.18)"/>
    <circle cx="75" cy="65" r="7" fill="rgba(180,220,255,0.18)"/>
    <line x1="62" y1="65" x2="68" y2="65"/>
  </g>
  <!-- glass shine -->
  <path d="M50,62 Q52,60 54,62" stroke="#fff" stroke-width="0.8" fill="none" opacity="0.6"/>
  <path d="M70,62 Q72,60 74,62" stroke="#fff" stroke-width="0.8" fill="none" opacity="0.6"/>

  <!-- EYES (through glasses) -->
  <ellipse cx="55" cy="65" rx="2.4" ry="3" fill="url(#alisya-eye)"/>
  <ellipse cx="75" cy="65" rx="2.4" ry="3" fill="url(#alisya-eye)"/>
  <ellipse cx="56" cy="64" rx="0.7" ry="0.7" fill="#fff"/>
  <ellipse cx="76" cy="64" rx="0.7" ry="0.7" fill="#fff"/>

  <!-- brows (sharp, determined) -->
  <path d="M50,55 L60,57" stroke="#1a0c05" stroke-width="1.4" stroke-linecap="round"/>
  <path d="M70,57 L80,55" stroke="#1a0c05" stroke-width="1.4" stroke-linecap="round"/>

  <!-- nose -->
  <path d="M62,68 Q63,76 65,77 Q67,76 68,68" stroke="#9c6e4d" stroke-width="0.4" fill="none" opacity="0.5"/>

  <!-- cheeks -->
  <ellipse cx="46" cy="74" rx="4.5" ry="3" fill="url(#alisya-cheek)"/>
  <ellipse cx="84" cy="74" rx="4.5" ry="3" fill="url(#alisya-cheek)"/>

  <!-- mouth (small smirk) -->
  <path d="M58,79 Q62,77 65,79 Q68,77 72,79" stroke="#7a3838" stroke-width="1.3" fill="none" stroke-linecap="round"/>

  <!-- HEADSET -->
  <path d="M40,55 Q65,30 90,55" stroke="#1a0c05" stroke-width="2.5" fill="none"/>
  <ellipse cx="38" cy="64" rx="4.5" ry="6.5" fill="#1a0c05"/>
  <ellipse cx="92" cy="64" rx="4.5" ry="6.5" fill="#1a0c05"/>
  <ellipse cx="38" cy="63" rx="2" ry="2.5" fill="#5fb3ff" opacity="0.4"/>
  <ellipse cx="92" cy="63" rx="2" ry="2.5" fill="#5fb3ff" opacity="0.4"/>

  <!-- CTO badge: code </> -->
  <rect x="38" y="135" width="10" height="10" rx="2" fill="#0d2238" stroke="#5fb3ff" stroke-width="0.8"/>
  <text x="43" y="143" text-anchor="middle" font-size="8" fill="#5fb3ff" font-family="monospace" font-weight="700">&lt;/&gt;</text>
</svg>

<svg class="think-bubble" viewBox="0 0 36 28" xmlns="http://www.w3.org/2000/svg">
  <circle cx="22" cy="11" r="10" fill="rgba(95,179,255,0.95)"/>
  <text x="22" y="15" text-anchor="middle" font-size="11" font-weight="700" fill="#fff" font-family="monospace">{ }</text>
  <circle cx="11" cy="22" r="2.5" fill="rgba(95,179,255,0.9)"/>
  <circle cx="6" cy="26" r="1.5" fill="rgba(95,179,255,0.85)"/>
</svg>
`,

  /* ────────────────────────────────────────────────────────────
     JULIA — CFO
     Auburn hair pulled back, pearl earring, business blazer
     Tone: polished, authoritative, warm
  ──────────────────────────────────────────────────────────── */
  julia: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Julia, CFO">
  <defs>
    <radialGradient id="julia-skin" cx="35%" cy="35%" r="75%">
      <stop offset="0%" stop-color="#ffe4cd"/>
      <stop offset="40%" stop-color="#f5c8a4"/>
      <stop offset="80%" stop-color="#d29b6e"/>
      <stop offset="100%" stop-color="#8a5e3a"/>
    </radialGradient>
    <radialGradient id="julia-cheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#e88a7c" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#e88a7c" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="julia-hair" x1="30%" y1="0%" x2="70%" y2="100%">
      <stop offset="0%" stop-color="#a85a2a"/>
      <stop offset="40%" stop-color="#7a3818"/>
      <stop offset="100%" stop-color="#3a1c08"/>
    </linearGradient>
    <linearGradient id="julia-blazer" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#e8a040"/>
      <stop offset="60%" stop-color="#a86820"/>
      <stop offset="100%" stop-color="#5e3a10"/>
    </linearGradient>
    <linearGradient id="julia-blouse" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#e8d8c0"/>
    </linearGradient>
    <radialGradient id="julia-eye" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#a87838"/>
      <stop offset="100%" stop-color="#4a2810"/>
    </radialGradient>
    <radialGradient id="julia-pearl" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="60%" stop-color="#f0e8e0"/>
      <stop offset="100%" stop-color="#c8b8a8"/>
    </radialGradient>
  </defs>

  <!-- hair back with bun -->
  <path d="M40,70 Q34,45 50,32 Q65,24 80,32 Q96,45 90,70 L88,82 Q82,72 78,68 L78,80 L52,80 L52,68 Q48,72 42,82 Z"
        fill="url(#julia-hair)"/>
  <!-- bun -->
  <ellipse cx="65" cy="24" rx="12" ry="9" fill="url(#julia-hair)"/>
  <ellipse cx="65" cy="22" rx="9" ry="6" fill="#5a3010" opacity="0.5"/>
  <ellipse cx="62" cy="20" rx="3" ry="2" fill="#a87838" opacity="0.6"/>

  <!-- neck -->
  <path d="M53,98 L53,116 Q65,122 77,116 L77,98 Z" fill="url(#julia-skin)"/>
  <ellipse cx="65" cy="106" rx="20" ry="5" fill="#000" opacity="0.2"/>

  <!-- blazer -->
  <path d="M26,160 L26,132 Q34,108 65,108 Q96,108 104,132 L104,160 Z" fill="url(#julia-blazer)"/>
  <path d="M26,160 L26,132 Q34,108 50,108 L48,160 Z" fill="#000" opacity="0.15"/>
  <!-- blouse under -->
  <path d="M55,108 L65,128 L75,108 L70,116 L65,120 L60,116 Z" fill="url(#julia-blouse)"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#julia-skin)"/>
  <ellipse cx="50" cy="48" rx="11" ry="13" fill="#fff" opacity="0.18"/>

  <!-- bangs (swept, mature) -->
  <path d="M42,44 Q44,32 56,32 Q60,42 58,52 L48,46 Q42,46 42,44 Z" fill="url(#julia-hair)"/>
  <path d="M88,44 Q86,32 74,32 Q70,42 72,52 L82,46 Q88,46 88,44 Z" fill="url(#julia-hair)"/>

  <!-- side hair -->
  <path d="M42,52 L42,76 L48,72 L48,52 Z" fill="url(#julia-hair)"/>
  <path d="M88,52 L88,76 L82,72 L82,52 Z" fill="url(#julia-hair)"/>

  <!-- PEARL EARRINGS -->
  <circle cx="41" cy="68" r="2" fill="url(#julia-pearl)"/>
  <circle cx="40.3" cy="67.3" r="0.6" fill="#fff"/>
  <circle cx="89" cy="68" r="2" fill="url(#julia-pearl)"/>
  <circle cx="88.3" cy="67.3" r="0.6" fill="#fff"/>

  <!-- brows (polished arch) -->
  <path d="M50,57 Q55,54 60,57" stroke="#3a1c08" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M70,57 Q75,54 80,57" stroke="#3a1c08" stroke-width="1.3" fill="none" stroke-linecap="round"/>

  <!-- EYES -->
  <ellipse cx="55" cy="66" rx="3.6" ry="4.2" fill="url(#julia-eye)"/>
  <ellipse cx="75" cy="66" rx="3.6" ry="4.2" fill="url(#julia-eye)"/>
  <ellipse cx="55" cy="66" rx="1.3" ry="1.3" fill="#0a0500"/>
  <ellipse cx="75" cy="66" rx="1.3" ry="1.3" fill="#0a0500"/>
  <ellipse cx="55.8" cy="65" rx="0.9" ry="0.9" fill="#fff"/>
  <ellipse cx="75.8" cy="65" rx="0.9" ry="0.9" fill="#fff"/>
  <!-- upper lash -->
  <path d="M51,63 Q55,61 59,63" stroke="#3a1c08" stroke-width="0.8" fill="none"/>
  <path d="M71,63 Q75,61 79,63" stroke="#3a1c08" stroke-width="0.8" fill="none"/>

  <!-- nose -->
  <path d="M62,68 Q63,76 65,77 Q67,76 68,68" stroke="#9c6e4d" stroke-width="0.4" fill="none" opacity="0.5"/>

  <!-- cheeks -->
  <ellipse cx="46" cy="74" rx="4.5" ry="3" fill="url(#julia-cheek)"/>
  <ellipse cx="84" cy="74" rx="4.5" ry="3" fill="url(#julia-cheek)"/>

  <!-- mouth (closed, polished smile) -->
  <path d="M58,79 Q65,82 72,79" stroke="#a04040" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M60,80 Q65,82 70,80" stroke="#c66060" stroke-width="0.5" fill="none" opacity="0.5"/>

  <!-- CFO brooch -->
  <circle cx="44" cy="138" r="4" fill="url(#julia-pearl)" stroke="#9a7a1c" stroke-width="0.5"/>
  <text x="44" y="141" text-anchor="middle" font-size="5" fill="#7a5a18" font-weight="700">$</text>
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
     Voluminous red-auburn curls, expressive green eyes, scarf
     Tone: creative, vibrant, energetic
  ──────────────────────────────────────────────────────────── */
  farah: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Farah, CMO">
  <defs>
    <radialGradient id="farah-skin" cx="35%" cy="35%" r="75%">
      <stop offset="0%" stop-color="#ffe0c8"/>
      <stop offset="40%" stop-color="#f5bfa0"/>
      <stop offset="80%" stop-color="#d89470"/>
      <stop offset="100%" stop-color="#8a5e3a"/>
    </radialGradient>
    <radialGradient id="farah-cheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ff7080" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#ff7080" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="farah-hair" x1="30%" y1="0%" x2="70%" y2="100%">
      <stop offset="0%" stop-color="#ff6a4a"/>
      <stop offset="40%" stop-color="#c83820"/>
      <stop offset="100%" stop-color="#7a1a08"/>
    </linearGradient>
    <radialGradient id="farah-curl" cx="35%" cy="35%" r="60%">
      <stop offset="0%" stop-color="#ff8a6a"/>
      <stop offset="100%" stop-color="#a02818"/>
    </radialGradient>
    <linearGradient id="farah-top" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#e91e63"/>
      <stop offset="60%" stop-color="#a01844"/>
      <stop offset="100%" stop-color="#5e0a22"/>
    </linearGradient>
    <radialGradient id="farah-eye" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#5fb088"/>
      <stop offset="60%" stop-color="#1e6850"/>
      <stop offset="100%" stop-color="#0a3020"/>
    </radialGradient>
  </defs>

  <!-- curly back hair -->
  <g fill="url(#farah-curl)">
    <circle cx="38" cy="50" r="11"/>
    <circle cx="92" cy="50" r="11"/>
    <circle cx="30" cy="65" r="10"/>
    <circle cx="100" cy="65" r="10"/>
    <circle cx="35" cy="80" r="9"/>
    <circle cx="95" cy="80" r="9"/>
    <ellipse cx="65" cy="92" rx="32" ry="14"/>
  </g>
  <!-- curl shine -->
  <circle cx="34" cy="46" r="3" fill="#ffb090" opacity="0.6"/>
  <circle cx="88" cy="46" r="3" fill="#ffb090" opacity="0.6"/>

  <!-- neck -->
  <path d="M54,96 L54,114 Q65,120 76,114 L76,96 Z" fill="url(#farah-skin)"/>
  <ellipse cx="65" cy="104" rx="18" ry="4" fill="#000" opacity="0.18"/>

  <!-- top -->
  <path d="M28,160 L28,128 Q36,108 65,108 Q94,108 102,128 L102,160 Z" fill="url(#farah-top)"/>
  <path d="M28,160 L28,128 Q36,108 50,108 L48,160 Z" fill="#000" opacity="0.15"/>
  <!-- scarf -->
  <path d="M48,108 Q52,118 56,108 Q60,116 64,108 Q68,116 72,108 Q76,118 80,108 L80,124 L48,124 Z"
        fill="#ffd1e0" opacity="0.75"/>
  <path d="M48,108 L48,124 L80,124 L80,108 Q70,116 65,114 Q60,116 48,108 Z" fill="#000" opacity="0.08"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#farah-skin)"/>
  <ellipse cx="50" cy="48" rx="11" ry="13" fill="#fff" opacity="0.18"/>

  <!-- curly bangs -->
  <g fill="url(#farah-curl)">
    <circle cx="48" cy="40" r="8"/>
    <circle cx="58" cy="34" r="9"/>
    <circle cx="68" cy="32" r="10"/>
    <circle cx="78" cy="36" r="8"/>
    <circle cx="44" cy="48" r="6"/>
    <circle cx="82" cy="48" r="6"/>
  </g>
  <!-- shine -->
  <circle cx="64" cy="30" r="3" fill="#ffb090" opacity="0.7"/>

  <!-- side curls -->
  <circle cx="40" cy="58" r="6" fill="url(#farah-curl)"/>
  <circle cx="90" cy="58" r="6" fill="url(#farah-curl)"/>

  <!-- brows (arched, expressive) -->
  <path d="M50,55 Q55,52 60,55" stroke="#a02818" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M70,55 Q75,52 80,55" stroke="#a02818" stroke-width="1.3" fill="none" stroke-linecap="round"/>

  <!-- EYES (bright green) -->
  <ellipse cx="55" cy="66" rx="3.8" ry="5" fill="url(#farah-eye)"/>
  <ellipse cx="75" cy="66" rx="3.8" ry="5" fill="url(#farah-eye)"/>
  <ellipse cx="55" cy="66" rx="1.4" ry="1.4" fill="#0a0500"/>
  <ellipse cx="75" cy="66" rx="1.4" ry="1.4" fill="#0a0500"/>
  <ellipse cx="55.8" cy="64.5" rx="1" ry="1.4" fill="#fff"/>
  <ellipse cx="75.8" cy="64.5" rx="1" ry="1.4" fill="#fff"/>
  <!-- eyelashes (defined) -->
  <path d="M50,62 L52,60" stroke="#a02818" stroke-width="1" stroke-linecap="round"/>
  <path d="M55,60 L57,58" stroke="#a02818" stroke-width="1" stroke-linecap="round"/>
  <path d="M73,58 L75,60" stroke="#a02818" stroke-width="1" stroke-linecap="round"/>
  <path d="M78,60 L80,62" stroke="#a02818" stroke-width="1" stroke-linecap="round"/>
  <!-- lower lash hint -->
  <path d="M51,68 Q55,70 59,68" stroke="#a02818" stroke-width="0.5" fill="none" opacity="0.6"/>
  <path d="M71,68 Q75,70 79,68" stroke="#a02818" stroke-width="0.5" fill="none" opacity="0.6"/>

  <!-- nose -->
  <path d="M62,68 Q63,76 65,77 Q67,76 68,68" stroke="#9c6e4d" stroke-width="0.4" fill="none" opacity="0.5"/>

  <!-- cheeks (more pink) -->
  <ellipse cx="46" cy="74" rx="5" ry="3.5" fill="url(#farah-cheek)"/>
  <ellipse cx="84" cy="74" rx="5" ry="3.5" fill="url(#farah-cheek)"/>

  <!-- mouth (slight smile) -->
  <path d="M58,79 Q65,82 72,79" stroke="#c84050" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <path d="M60,80 Q65,82 70,80" stroke="#e86070" stroke-width="0.5" fill="none" opacity="0.6"/>

  <!-- CMO star badge -->
  <path d="M44,134 L46,138 L50,138 L47,141 L48,145 L44,143 L40,145 L41,141 L38,138 L42,138 Z"
        fill="#ffd966" stroke="#b88a1f" stroke-width="0.5"/>
  <ellipse cx="43" cy="140" rx="1.5" ry="1" fill="#fff8c0" opacity="0.7"/>
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
     Sleek black hair in side ponytail, mint scarf, professional
     Tone: organized, sharp, modern
  ──────────────────────────────────────────────────────────── */
  delisha: () => `
<svg class="avatar-svg" viewBox="0 0 130 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Delisha, COO">
  <defs>
    <radialGradient id="delisha-skin" cx="35%" cy="35%" r="75%">
      <stop offset="0%" stop-color="#fde0c8"/>
      <stop offset="40%" stop-color="#f0c5a4"/>
      <stop offset="80%" stop-color="#cf9670"/>
      <stop offset="100%" stop-color="#8a5a3a"/>
    </radialGradient>
    <radialGradient id="delisha-cheek" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#e88595" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#e88595" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="delisha-hair" x1="30%" y1="0%" x2="70%" y2="100%">
      <stop offset="0%" stop-color="#3a2820"/>
      <stop offset="50%" stop-color="#1a0e08"/>
      <stop offset="100%" stop-color="#0a0402"/>
    </linearGradient>
    <linearGradient id="delisha-shine" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#7a5a40" stop-opacity="0.7"/>
      <stop offset="100%" stop-color="#7a5a40" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="delisha-shirt" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#6ee7b7"/>
      <stop offset="60%" stop-color="#2fa97a"/>
      <stop offset="100%" stop-color="#0e5a40"/>
    </linearGradient>
    <radialGradient id="delisha-eye" cx="40%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#6e9a55"/>
      <stop offset="60%" stop-color="#2e5a20"/>
      <stop offset="100%" stop-color="#0a2a08"/>
    </radialGradient>
  </defs>

  <!-- ponytail (back, swept right) -->
  <path d="M85,42 Q110,50 108,80 Q106,100 100,108 Q98,98 96,90 Q92,82 88,75 Z" fill="url(#delisha-hair)"/>
  <ellipse cx="103" cy="90" rx="6" ry="14" fill="url(#delisha-hair)"/>
  <ellipse cx="103" cy="86" rx="3" ry="6" fill="url(#delisha-shine)" opacity="0.5"/>

  <!-- main hair back -->
  <path d="M40,68 Q34,42 52,30 Q65,24 78,30 Q96,42 90,68 L88,82 Q84,72 80,68 L80,80 L50,80 L50,68 Q46,72 42,82 Z"
        fill="url(#delisha-hair)"/>
  <path d="M52,32 Q65,28 78,32 Q70,26 65,26 Q60,26 52,32 Z" fill="url(#delisha-shine)"/>

  <!-- neck -->
  <path d="M53,98 L53,116 Q65,122 77,116 L77,98 Z" fill="url(#delisha-skin)"/>
  <ellipse cx="65" cy="106" rx="20" ry="5" fill="#000" opacity="0.2"/>

  <!-- shirt -->
  <path d="M26,160 L26,134 Q34,108 65,108 Q96,108 104,134 L104,160 Z" fill="url(#delisha-shirt)"/>
  <path d="M26,160 L26,134 Q34,108 50,108 L48,160 Z" fill="#000" opacity="0.15"/>
  <!-- collar V -->
  <path d="M55,108 L65,124 L75,108 L70,116 L65,120 L60,116 Z" fill="#fff4ec"/>

  <!-- face -->
  <ellipse cx="65" cy="62" rx="25" ry="29" fill="url(#delisha-skin)"/>
  <ellipse cx="50" cy="48" rx="11" ry="13" fill="#fff" opacity="0.18"/>

  <!-- asymmetric bangs -->
  <path d="M40,44 Q44,30 60,30 Q66,38 64,52 L52,46 Q42,46 40,44 Z" fill="url(#delisha-hair)"/>
  <path d="M70,40 Q72,32 82,30 Q90,32 90,42 Q86,46 78,46 Q72,46 70,40 Z" fill="url(#delisha-hair)"/>

  <!-- side hair -->
  <path d="M40,52 L40,76 L46,72 L46,52 Z" fill="url(#delisha-hair)"/>
  <path d="M88,52 L88,76 L82,72 L82,52 Z" fill="url(#delisha-hair)"/>

  <!-- hair tie -->
  <ellipse cx="100" cy="50" rx="5" ry="4" fill="#f4cf6a"/>
  <ellipse cx="98" cy="48" rx="1.5" ry="1" fill="#fff8d0"/>

  <!-- brows (focused) -->
  <path d="M50,57 Q55,54 60,57" stroke="#0a0402" stroke-width="1.3" fill="none" stroke-linecap="round"/>
  <path d="M70,57 Q75,54 80,57" stroke="#0a0402" stroke-width="1.3" fill="none" stroke-linecap="round"/>

  <!-- EYES (bright green) -->
  <ellipse cx="55" cy="66" rx="3.5" ry="4.5" fill="url(#delisha-eye)"/>
  <ellipse cx="75" cy="66" rx="3.5" ry="4.5" fill="url(#delisha-eye)"/>
  <ellipse cx="55" cy="66" rx="1.3" ry="1.3" fill="#0a0500"/>
  <ellipse cx="75" cy="66" rx="1.3" ry="1.3" fill="#0a0500"/>
  <ellipse cx="55.7" cy="64.5" rx="1" ry="1.2" fill="#fff"/>
  <ellipse cx="75.7" cy="64.5" rx="1" ry="1.2" fill="#fff"/>
  <path d="M51,63 Q55,61 59,63" stroke="#0a0402" stroke-width="0.7" fill="none"/>
  <path d="M71,63 Q75,61 79,63" stroke="#0a0402" stroke-width="0.7" fill="none"/>

  <!-- nose -->
  <path d="M62,68 Q63,76 65,77 Q67,76 68,68" stroke="#9c6e4d" stroke-width="0.4" fill="none" opacity="0.5"/>

  <!-- cheeks -->
  <ellipse cx="46" cy="74" rx="4.5" ry="3" fill="url(#delisha-cheek)"/>
  <ellipse cx="84" cy="74" rx="4.5" ry="3" fill="url(#delisha-cheek)"/>

  <!-- mouth (gentle smile) -->
  <path d="M58,79 Q65,82 72,79" stroke="#a04050" stroke-width="1.4" fill="none" stroke-linecap="round"/>
  <path d="M60,80 Q65,82 70,80" stroke="#c66070" stroke-width="0.5" fill="none" opacity="0.5"/>

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

// Helper: render avatar by id (unchanged)
function renderAvatar(id) {
  if (!AVATARS[id]) {
    return `<div class="avatar-svg" style="display:flex;align-items:center;justify-content:center;color:#888">?</div>`;
  }
  return AVATARS[id]() +
    `<div class="typing-dots"><span></span><span></span><span></span></div>`;
}

window.AVATARS = AVATARS;
window.renderAvatar = renderAvatar;
