const API = window.location.origin;

let catalog = [];
let selected = null;
let sessionToken = localStorage.getItem("game_donat_session") || "";

const icons = {
  "PUBG Mobile": "🔫",
  "Free Fire": "🔥",
  "Grand Mobile": "🚗",
  "Telegram Premium": "⭐",
  "Mobile Legends": "⚔️"
};

function money(v) {
  return Number(v || 0).toLocaleString("uz-UZ") + " so'm";
}

function showNotice(msg) {
  const n = document.getElementById("notice");
  if (!n) return;
  n.textContent = msg;
  n.classList.remove("hidden");
  setTimeout(() => n.classList.add("hidden"), 4500);
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (sessionToken) {
    headers.Authorization = "Bearer " + sessionToken;
  }

  try {
    const r = await fetch(API + path, {
      ...options,
      headers
    });

    let d = {};
    try {
      d = await r.json();
    } catch {}

    if (!r.ok && !d.error) {
      d.error = "Server xatosi";
    }

    return d;
  } catch (e) {
    return {
      ok: false,
      error: "Server bilan bog‘lanib bo‘lmadi."
    };
  }
}

async function loadCatalog() {
  const games = document.getElementById("games");

  if (games) {
    games.innerHTML =
      '<div class="loading">⏳ Katalog yuklanmoqda...</div>';
  }

  const d = await api("/api/catalog");

  if (!d.ok) {
    if (games) {
      games.innerHTML =
        '<div class="loading">❌ Katalogni yuklab bo‘lmadi.</div>';
    }
    return;
  }

  catalog = d.games || [];

  renderGames();
  refreshMe();
}

function renderGames() {
  const box = document.getElementById("games");

  if (!box) return;

  if (!catalog.length) {
    box.innerHTML =
      '<div class="loading">O‘yinlar topilmadi.</div>';
    return;
  }

  box.innerHTML = catalog.map((g, i) => `
    <div class="game-card">

      <div class="game-icon">
        ${icons[g.name] || "🎮"}
      </div>

      <h3>${esc(g.name)}</h3>

      <p>
        ${g.manual ? "Manual buyurtma" : "API orqali donat"}
      </p>

      <div class="packages">

        ${(g.packages || []).map(p => `
          <div class="package">

            <h3>${esc(p.name)}</h3>

            <div class="price">
              ${money(p.price)}
            </div>

            <button
              type="button"
              onclick="openOrder(${i}, ${p.paket_id})">
              🛒 Xarid qilish
            </button>

          </div>
        `).join("")}

      </div>

    </div>
  `).join("");
}

function openOrder(gameIndex, paketId) {
  const g = catalog[gameIndex];

  if (!g) return;

  const p = (g.packages || []).find(
    x => x.paket_id === paketId
  );

  if (!p) return;

  selected = {
    game: g,
    package: p
  };

  const title = document.getElementById("orderTitle");
  const pack = document.getElementById("orderPackage");
  const player = document.getElementById("playerId");
  const server = document.getElementById("serverId");
  const result = document.getElementById("checkResult");
  const orderBtn = document.getElementById("orderBtn");
  const modal = document.getElementById("orderModal");

  if (title) {
    title.textContent = "🛒 " + g.name;
  }

  if (pack) {
    pack.textContent =
      `${p.name} — ${money(p.price)}`;
  }

  if (player) {
    player.placeholder =
      g.id_label || "Player ID";
    player.value = "";
  }

  if (server) {
    server.value = "";
    server.classList.toggle(
      "hidden",
      !g.requires_server
    );
  }

  if (result) {
    result.textContent = "";
  }

  if (orderBtn) {
    orderBtn.classList.add("hidden");
  }

  if (modal) {
    modal.classList.remove("hidden");
  }
}

function closeOrder() {
  const modal = document.getElementById("orderModal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

function openLogin() {
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.classList.remove("hidden");
  }
}

function closeLogin() {
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.classList.add("hidden");
  }
}

async function checkId() {
  if (!selected) return;

  const playerEl = document.getElementById("playerId");
  const serverEl = document.getElementBy
