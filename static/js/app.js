/* ============================================================
   Saga X — Agent Desk dashboard client
   Polls /api/state every 3s, renders 5 agent cards with
   state-driven animation classes.
   ============================================================ */

(() => {
  "use strict";

  const POLL_INTERVAL_MS = 3000;
  const TIMEOUT_MS = 8000;

  const ORDER = ["putri", "alisya", "julia", "farah", "delisha"];
  const STATE_LABELS = {
    idle: "Idle",
    thinking: "Thinking…",
    working: "Working…",
    done: "Done",
    error: "Error",
    offline: "Offline",
  };

  const $agents = document.getElementById("agents");
  const $lastUpdated = document.getElementById("last-updated");
  const $connStatus = document.getElementById("conn-status");

  // ─── Initial render (placeholders so layout doesn't jump) ───
  function skeletonCard(id) {
    const agent = (window.AVATARS && id) ? null : null;
    const avatarHTML = window.renderAvatar(id);
    return `
<article class="card" data-agent="${id}" data-state="idle">
  <div class="avatar-wrap">${avatarHTML}</div>
  <header class="card-header">
    <div class="agent-name">…</div>
    <span class="agent-role role-${id}">…</span>
  </header>
  <div class="state-badge"><span class="dot"></span><span class="state-label">…</span></div>
  <div class="task">…</div>
  <div class="updated">…</div>
</article>`;
  }

  function init() {
    $agents.innerHTML = ORDER.map(skeletonCard).join("");
  }

  // ─── Update one card with new data ─────────────────────────
  function updateCard(id, data) {
    const card = document.querySelector(`[data-agent="${id}"]`);
    if (!card) return;

    // state change → swap class, trigger CSS animation
    const prevState = card.getAttribute("data-state");
    const newState = data.state || "idle";
    if (prevState !== newState) {
      // For "done" we want a single bounce, so force animation reset
      if (newState === "done") {
        card.style.animation = "none";
        // force reflow
        // eslint-disable-next-line no-unused-expressions
        card.offsetHeight;
        card.style.animation = "";
      }
      card.setAttribute("data-state", newState);
    }

    card.querySelector(".agent-name").textContent = data.name || id;
    const roleEl = card.querySelector(".agent-role");
    roleEl.textContent = data.role || "";
    roleEl.className = `agent-role role-${id}`;

    card.querySelector(".state-label").textContent = STATE_LABELS[newState] || newState;

    const taskEl = card.querySelector(".task");
    const toolBit = data.current_tool ? ` · ${data.current_tool}` : "";
    taskEl.textContent = (data.task || "—") + (toolBit ? toolBit : "");

    const updatedEl = card.querySelector(".updated");
    if (data.updated_at) {
      card.dataset.updatedAt = String(data.updated_at);
      updatedEl.textContent = `updated ${formatRelative(data.updated_at)}`;
    } else {
      delete card.dataset.updatedAt;
      updatedEl.textContent = "no activity yet";
    }
  }

  function formatRelative(ts) {
    const diff = Math.floor(Date.now() / 1000) - ts;
    if (diff < 5) return "just now";
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(ts * 1000).toLocaleString();
  }

  // ─── Fetch state with timeout ─────────────────────────────
  async function fetchState() {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    try {
      const res = await fetch("/api/state", { signal: ctrl.signal, cache: "no-store" });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      applyState(data);
      setConn(true);
    } catch (err) {
      clearTimeout(timer);
      setConn(false, err.message || "network error");
    }
  }

  function applyState(data) {
    for (const id of ORDER) {
      const d = data[id];
      if (d) updateCard(id, d);
    }
    $lastUpdated.textContent = `live · ${new Date().toLocaleTimeString()}`;
    // Feed the same state to the chat sidebar so it cannot drift from
    // the cards by polling separately.
    if (window.__sagaxChat) window.__sagaxChat.paintStates(data);
  }

  function setConn(ok, msg) {
    if (ok) {
      $connStatus.textContent = "●";
      $connStatus.className = "status-pill status-pill--live";
      $connStatus.title = "Connected";
    } else {
      $connStatus.textContent = "●";
      $connStatus.className = "status-pill status-pill--error";
      $connStatus.title = `Disconnected: ${msg || ""}`;
      $lastUpdated.textContent = `reconnecting…`;
    }
  }

  // ─── Periodic refresh of "X ago" labels ───────────────────
  function refreshRelative() {
    for (const id of ORDER) {
      const card = document.querySelector(`[data-agent="${id}"]`);
      if (!card) continue;
      const updatedEl = card.querySelector(".updated");
      const current = updatedEl.textContent;
      if (current === "no activity yet") continue;
      // Re-fetch updated_at from data-state attribute
      const dataUpdatedAt = card.dataset.updatedAt;
      if (dataUpdatedAt) {
        updatedEl.textContent = `updated ${formatRelative(parseInt(dataUpdatedAt, 10))}`;
      }
    }
  }

  // ─── Boot ─────────────────────────────────────────────────
  init();
  fetchState();
  setInterval(fetchState, POLL_INTERVAL_MS);
  setInterval(refreshRelative, 1000);

  // Expose for debug
  window.__sagax = { fetchState, updateCard };
})();
