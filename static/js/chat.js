/* ============================================================
   Saga X Agent Desk — chat + approvals
   ============================================================ */

(() => {
  "use strict";

  const AGENTS = [
    { id: "putri",   name: "Putri",   role: "CEO" },
    { id: "alisya",  name: "Alisya",  role: "CTO" },
    { id: "julia",   name: "Julia",   role: "CFO" },
    { id: "farah",   name: "Farah",   role: "CMO" },
    { id: "delisha", name: "Delisha", role: "COO" },
  ];

  let current = "delisha";
  let sending = false;

  const $ = (sel) => document.querySelector(sel);

  // ── Session ───────────────────────────────────────────────
  // The server hands out an HttpOnly cookie in exchange for the token,
  // so nothing here ever holds the token itself. Any 401 from any call
  // brings the sign-in card back rather than failing quietly.
  function showSignin(show, message) {
    const box = $("#signin");
    if (box) box.hidden = !show;
    const err = $("#signin-error");
    if (err) { err.hidden = !message; err.textContent = message || ""; }
    if (show) { const t = $("#signin-token"); if (t) t.focus(); }
  }

  async function api(path, options) {
    const res = await fetch(path, Object.assign({ cache: "no-store" }, options));
    if (res.status === 401) {
      showSignin(true, "Sesi tamat. Masuk semula.");
      throw new Error("unauthorised");
    }
    return res;
  }

  async function checkSession() {
    try {
      const res = await fetch("/api/session", { cache: "no-store" });
      const data = await res.json();
      showSignin(data.auth_required && !data.signed_in);
    } catch (err) {
      // If this fails the network is down; the sign-in card would be
      // misleading, so leave the page as it is.
    }
  }

  async function signIn(e) {
    e.preventDefault();
    const btn = $("#signin-go");
    const field = $("#signin-token");
    btn.disabled = true;
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: field.value }),
      });
      if (res.ok) {
        field.value = "";
        showSignin(false);
        loadThread(current);
        refreshApprovalCount();
      } else {
        showSignin(true, "Token tidak sah.");
      }
    } catch (err) {
      showSignin(true, "Tak dapat menghubungi pelayan.");
    } finally {
      btn.disabled = false;
    }
  }

  // ── Web push ──────────────────────────────────────────────
  // Permission must come from a real tap. Asking on page load gets the
  // request denied permanently on some browsers, and on iOS it is
  // ignored outright unless the PWA was added to the Home Screen.
  function b64ToBytes(b64) {
    const pad = "=".repeat((4 - (b64.length % 4)) % 4);
    const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, (c) => c.charCodeAt(0));
  }

  const pushSupported = () =>
    "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

  // iOS only allows push from an installed PWA, so say that rather than
  // letting the button fail silently on an iPhone.
  const isIOS = () => /iPad|iPhone|iPod/.test(navigator.userAgent);
  const isStandalone = () =>
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

  async function initPush() {
    const btn = $("#push-btn");
    if (!btn || !pushSupported()) return;
    btn.hidden = false;

    let reg;
    try {
      reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    } catch (err) {
      btn.hidden = true;
      return;
    }

    const existing = await reg.pushManager.getSubscription();
    paintPush(!!existing);

    btn.addEventListener("click", async () => {
      if (isIOS() && !isStandalone()) {
        alert("Di iPhone/iPad, tambah desk ini ke Skrin Utama dahulu " +
              "(Kongsi → Add to Home Screen), kemudian buka dari sana.");
        return;
      }
      btn.disabled = true;
      try {
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
          await fetch("/api/push/unsubscribe", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ endpoint: sub.endpoint }),
          });
          await sub.unsubscribe();
          paintPush(false);
          return;
        }
        if ((await Notification.requestPermission()) !== "granted") {
          paintPush(false);
          return;
        }
        const keyRes = await fetch("/api/push/key");
        const { public_key: key, configured } = await keyRes.json();
        if (!configured || !key) {
          alert("Push belum dikonfigurasi di pelayan (VAPID keys).");
          return;
        }
        const fresh = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: b64ToBytes(key),
        });
        const res = await api("/api/push/subscribe", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ subscription: fresh.toJSON() }),
        });
        paintPush(res.ok);
      } catch (err) {
        paintPush(false);
      } finally {
        btn.disabled = false;
      }
    });
  }

  function paintPush(on) {
    const btn = $("#push-btn");
    if (!btn) return;
    btn.dataset.on = String(!!on);
    btn.title = on ? "Notifikasi hidup — klik untuk matikan"
                   : "Hidupkan notifikasi";
  }

  // ── Tabs ──────────────────────────────────────────────────
  function showPanel(name) {
    document.querySelectorAll(".tab").forEach((t) => {
      t.setAttribute("aria-selected", String(t.dataset.panel === name));
    });
    document.querySelectorAll(".panel").forEach((p) => {
      p.hidden = p.dataset.panel !== name;
    });
    if (name === "chat") loadThread(current);
    if (name === "approvals") loadApprovals();
    if (name === "activity") loadActivity();
  }

  // ── Agent list ────────────────────────────────────────────
  function renderPeople() {
    $("#chat-list").innerHTML = AGENTS.map((a) => `
<button class="chat-person" data-agent="${a.id}"
        aria-current="${a.id === current}">
  <span class="pip" data-state="idle"></span>
  <span class="who"><span>${a.name}</span><span class="role">${a.role}</span></span>
</button>`).join("");
  }

  // Reuse the state the desk already polls, so the chat list shows the
  // same truth as the cards rather than a second, drifting copy.
  function paintStates(state) {
    for (const a of AGENTS) {
      const pip = document.querySelector(`.chat-person[data-agent="${a.id}"] .pip`);
      if (pip && state[a.id]) pip.dataset.state = state[a.id].state || "idle";
    }
  }

  // ── Thread ────────────────────────────────────────────────
  function bubble(role, text, pending) {
    const div = document.createElement("div");
    div.className = `msg ${role}${pending ? " pending" : ""}`;
    div.textContent = text;
    return div;
  }

  async function loadThread(agent) {
    current = agent;
    document.querySelectorAll(".chat-person").forEach((b) => {
      b.setAttribute("aria-current", String(b.dataset.agent === agent));
    });
    const who = AGENTS.find((a) => a.id === agent);
    $("#chat-who").textContent = who ? who.name : agent;
    $("#chat-role").textContent = who ? who.role : "";

    const thread = $("#chat-thread");
    thread.innerHTML = "";
    try {
      const res = await fetch(`/api/chat/${agent}`, { cache: "no-store" });
      const data = await res.json();
      if (!data.messages || !data.messages.length) {
        thread.innerHTML = `<div class="chat-empty">
Belum ada perbualan dengan ${who ? who.name : agent}.<br>
Beri dia satu tugasan.</div>`;
        return;
      }
      for (const m of data.messages) thread.appendChild(bubble(m.role, m.content));
      thread.scrollTop = thread.scrollHeight;
    } catch (err) {
      thread.innerHTML = `<div class="chat-empty">Tak dapat memuatkan perbualan.</div>`;
    }
  }

  async function send() {
    if (sending) return;
    const box = $("#chat-input");
    const text = box.value.trim();
    if (!text) return;

    sending = true;
    $("#chat-send").disabled = true;
    box.value = "";

    const thread = $("#chat-thread");
    if (thread.querySelector(".chat-empty")) thread.innerHTML = "";
    thread.appendChild(bubble("user", text));
    // A model call takes seconds. Say so, rather than looking frozen.
    const waiting = bubble("assistant", "…", true);
    thread.appendChild(waiting);
    thread.scrollTop = thread.scrollHeight;

    try {
      const res = await api(`/api/chat/${current}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      waiting.classList.remove("pending");
      waiting.textContent = data.reply || data.error || "(tiada jawapan)";
      if (data.cost_usd != null) {
        const cached = data.input_tokens
          ? Math.round((data.cached_tokens / data.input_tokens) * 100) : 0;
        $("#chat-spend").textContent =
          `$${Number(data.cost_usd).toFixed(4)} · cache ${cached}%`;
      }
      // An approval may have just been queued.
      if (data.status === "needs_approval") refreshApprovalCount();
    } catch (err) {
      waiting.classList.remove("pending");
      waiting.textContent = err && err.message === "unauthorised"
        ? "🔒 Sesi tamat — masuk semula."
        : "⚠️ Gagal menghantar.";
    } finally {
      sending = false;
      $("#chat-send").disabled = false;
      thread.scrollTop = thread.scrollHeight;
      box.focus();
    }
  }

  // ── Approvals ─────────────────────────────────────────────
  function money(a) {
    if (a.amount == null) return "";
    return `<span class="amount">${a.currency || "MYR"} ${Number(a.amount)
      .toLocaleString("en-MY", { minimumFractionDigits: 2 })}</span>`;
  }

  async function loadApprovals() {
    const wrap = $("#approvals-wrap");
    try {
      const res = await fetch("/api/approvals", { cache: "no-store" });
      const data = await res.json();
      const rows = data.approvals || [];
      if (!rows.length) {
        wrap.innerHTML = `<div class="approvals-empty">
Tiada apa-apa menunggu kelulusan.</div>`;
        return;
      }
      wrap.innerHTML = rows.map((a) => `
<article class="approval" data-risk="${a.risk}" data-id="${a.id}">
  <div class="summary">${escapeHtml(a.summary)}</div>
  <div class="meta">
    <span>${a.agent}</span>
    <span>${escapeHtml(a.action_type)}</span>
    ${money(a)}
    <span>luput ${new Date(a.expires_at).toLocaleString("en-MY")}</span>
  </div>
  <div class="actions">
    <button class="approve">Lulus</button>
    <button class="reject">Tolak</button>
  </div>
</article>`).join("");
    } catch (err) {
      wrap.innerHTML = `<div class="approvals-empty">Tak dapat memuatkan kelulusan.</div>`;
    }
  }

  async function decide(card, action) {
    const id = card.dataset.id;
    card.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      const res = await api(`/api/approvals/${id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const data = await res.json();
      if (data.error) {
        card.querySelector(".meta").innerHTML =
          `<span style="color:var(--c-error)">${escapeHtml(data.error)}</span>`;
        card.querySelectorAll("button").forEach((b) => (b.disabled = false));
        return;
      }
      card.querySelector(".actions").innerHTML =
        action === "approve"
          ? `<span style="color:var(--c-done)">✓ Diluluskan${
              data.result && data.result.number ? " — " + data.result.number : ""}</span>`
          : `<span style="color:var(--text-faint)">Ditolak</span>`;
      refreshApprovalCount();
    } catch (err) {
      card.querySelectorAll("button").forEach((b) => (b.disabled = false));
    }
  }

  async function refreshApprovalCount() {
    try {
      const res = await fetch("/api/approvals", { cache: "no-store" });
      const data = await res.json();
      const tab = document.querySelector('.tab[data-panel="approvals"]');
      const n = data.count || 0;
      tab.innerHTML = `Kelulusan${n ? ` <span class="badge">${n}</span>` : ""}`;
    } catch (err) { /* leave the tab as it is */ }
  }

  // ── Activity ──────────────────────────────────────────────
  function when(ts) {
    if (!ts) return "";
    const d = new Date(ts);
    const mins = Math.round((Date.now() - d) / 60000);
    if (mins < 60) return `${mins}m lalu`;
    if (mins < 1440) return `${Math.round(mins / 60)}j lalu`;
    return d.toLocaleDateString("en-MY", { day: "numeric", month: "short" });
  }

  function section(title, items) {
    return `<div class="act-section"><h3>${title}</h3><div class="act-list">${
      items.length ? items.join("")
                   : '<div class="act-empty">Tiada.</div>'}</div></div>`;
  }

  function row(status, whenTs, who, what, right) {
    return `<div class="act-item" data-status="${status || ""}">
  <span class="when">${when(whenTs)}</span>
  <span class="who">${escapeHtml(who || "")}</span>
  <span class="what">${escapeHtml(what || "")}</span>
  ${right ? `<span class="cost">${escapeHtml(right)}</span>` : ""}
</div>`;
  }

  async function loadActivity() {
    const body = $("#activity-body");
    const days = $("#activity-range").value;
    body.innerHTML = '<div class="act-empty">Memuatkan…</div>';
    try {
      const res = await api(`/api/activity?days=${days}`);
      const d = await res.json();
      const s = d.spend, c = d.counts;

      const stats = `<div class="stat-row">
  <div class="stat"><div class="n">${c.runs}</div><div class="k">Larian</div></div>
  <div class="stat ${c.failed_runs ? "bad" : ""}"><div class="n">${c.failed_runs}</div><div class="k">Gagal</div></div>
  <div class="stat ${c.open_incidents ? "bad" : "good"}"><div class="n">${c.open_incidents}</div><div class="k">Incident terbuka</div></div>
  <div class="stat ${c.pending_approvals ? "warn" : ""}"><div class="n">${c.pending_approvals}</div><div class="k">Menunggu lulus</div></div>
  <div class="stat"><div class="n">$${s.window_usd.toFixed(2)}</div><div class="k">Belanja tetingkap</div></div>
  <div class="stat ${s.cap_pct > 80 ? "bad" : s.cap_pct > 50 ? "warn" : "good"}">
    <div class="n">${s.cap_pct}%</div><div class="k">Had bulanan · $${s.month_usd.toFixed(2)}/$${s.cap_usd}</div></div>
  <div class="stat good"><div class="n">${s.cache_pct}%</div><div class="k">Cache</div></div>
</div>`;

      const byAgent = s.by_agent.map((a) =>
        row("", null, a.agent, `${a.runs} larian`, `$${Number(a.cost_usd || 0).toFixed(4)}`));
      const byAssign = s.by_assignment.map((a) =>
        row("", null, a.agent, a.title, `${a.runs}× · $${Number(a.cost_usd || 0).toFixed(4)}`));

      const incidents = d.incidents.map((i) =>
        row(i.status, i.opened_at, i.severity,
            `${i.title}${i.target ? " — " + i.target : ""}`, i.status));

      const approvals = d.approvals.map((a) =>
        row(a.status, a.requested_at, a.agent, a.summary,
            a.amount ? `${a.currency} ${Number(a.amount).toLocaleString("en-MY")}` : a.status));

      const runs = d.runs.map((r) =>
        row(r.status, r.queued_at, r.agent,
            (r.assignment_title ? `[${r.assignment_title}] ` : "") +
            (r.instruction || "").slice(0, 110),
            `${r.trigger_kind} · $${Number(r.cost_usd || 0).toFixed(4)}`));

      body.innerHTML = stats
        + section("Belanja ikut ejen", byAgent)
        + (byAssign.length ? section("Belanja ikut assignment", byAssign) : "")
        + section("Incident", incidents)
        + section("Kelulusan", approvals)
        + section("Larian", runs);
    } catch (err) {
      if (!(err && err.message === "unauthorised")) {
        body.innerHTML = '<div class="act-empty">Tak dapat memuatkan aktiviti.</div>';
      }
    }
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  // ── Wiring ────────────────────────────────────────────────
  function init() {
    renderPeople();

    document.querySelectorAll(".tab").forEach((t) => {
      t.addEventListener("click", () => showPanel(t.dataset.panel));
    });

    $("#chat-list").addEventListener("click", (e) => {
      const btn = e.target.closest(".chat-person");
      if (btn) loadThread(btn.dataset.agent);
    });

    $("#chat-send").addEventListener("click", send);
    $("#chat-input").addEventListener("keydown", (e) => {
      // Enter sends; Shift+Enter is a newline.
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    });

    $("#approvals-wrap").addEventListener("click", (e) => {
      const card = e.target.closest(".approval");
      if (!card) return;
      if (e.target.classList.contains("approve")) decide(card, "approve");
      if (e.target.classList.contains("reject")) decide(card, "reject");
    });

    const range = $("#activity-range");
    if (range) range.addEventListener("change", loadActivity);

    const form = $("#signin-form");
    if (form) form.addEventListener("submit", signIn);

    checkSession();
    initPush();
    refreshApprovalCount();
    setInterval(refreshApprovalCount, 30000);
  }

  window.__sagaxChat = { paintStates, loadThread };
  document.addEventListener("DOMContentLoaded", init);
})();
