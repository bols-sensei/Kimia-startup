/* Coquille : garde d'accès, menu filtré par permission, temps réel */

import { api, session } from "../services/api.js";
import { connect, onEvent } from "../services/websocket.js";
import { store } from "../state/store.js";
import * as ui from "../utils/ui.js";

const ICONS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  requests: '<path d="M3 13l3-8h12l3 8v6H3z"/><path d="M3 13h5l1 3h6l1-3h5"/>',
  clients: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 010 7M18 14.8c1.9.7 3.1 2.4 3.5 5.2"/>',
  projects: '<path d="M3 6.5A1.5 1.5 0 014.5 5h4l2 2.5h9A1.5 1.5 0 0121 9v9.5a1.5 1.5 0 01-1.5 1.5h-15A1.5 1.5 0 013 18.5z"/>',
  activities: '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M8 12.5l3 3 5-6"/>',
  planning: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  publications: '<path d="M4 10v4h3l7 4V6L7 10z"/><path d="M18 9.5a4 4 0 010 5"/>',
  portfolio: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
  services: '<path d="M12 2l3 6 6 1-4.5 4.5L18 20l-6-3-6 3 1.5-6.5L3 9l6-1z"/>',
  team: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.7-4 3.6-6 7-6s6.3 2 7 6"/>',
  documents: '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h6"/>',
  finances: '<circle cx="12" cy="12" r="8.5"/><path d="M14.5 9.2c-.6-.8-1.5-1.2-2.6-1.2-1.5 0-2.6.8-2.6 2 0 3 5.4 1.3 5.4 4.2 0 1.2-1.2 2-2.8 2-1.2 0-2.3-.5-2.9-1.4M12 6.5v1.5M12 16v1.5"/>',
  notifications: '<path d="M6 16V11a6 6 0 0112 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 004 0"/>',
  security: '<path d="M12 3l7.5 3v5.5c0 4.5-3 8-7.5 9.5-4.5-1.5-7.5-5-7.5-9.5V6z"/><path d="M9 12l2.2 2.2L15.5 10"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>',
  chat: '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>',
  logout: '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  menu: '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
};

export const MENU = [
  { id: "dashboard", label: "Tableau de bord", perm: "dashboard.view", icon: ICONS.dashboard },
  { id: "chat", label: "Chat", perm: null, icon: ICONS.chat },                     // ← accessible à tous
  { id: "requests", label: "Demandes", perm: "requests.view", icon: ICONS.requests },
  { id: "clients", label: "Clients", perm: "clients.view", icon: ICONS.clients },
  { id: "projects", label: "Projets", perm: "projects.view", icon: ICONS.projects },
  { id: "activities", label: "Activités", perm: "activities.view", icon: ICONS.activities },
  { id: "planning", label: "Planning", perm: "planning.view", icon: ICONS.planning },
  { id: "publications", label: "Publications", perm: "publications.view", icon: ICONS.publications },
  { id: "portfolio", label: "Réalisations", perm: "portfolio.view", icon: ICONS.portfolio },
  { id: "services", label: "Services", perm: "services.view", icon: ICONS.services },
  { id: "team", label: "Équipe", perm: "team.view", icon: ICONS.team },
  { id: "documents", label: "Documents", perm: "documents.view", icon: ICONS.documents },
  { id: "finances", label: "Finances", perm: "finance.view", icon: ICONS.finances },
  { id: "notifications", label: "Notifications", perm: "notifications.view", icon: ICONS.notifications },
  { id: "security", label: "Sécurité", perm: "security.view", icon: ICONS.security },
  { id: "settings", label: "Paramètres", perm: "team.manage", icon: ICONS.settings },
];

let user, view, current = null, loadToken = 0, reloadTimer = 0;

const allowed = (perm) => {
  if (!perm) return true;
  const perms = user?.permissions || [];
  if (perms.includes("*")) return true;
  return perms.includes(perm);
};

/* Frame */
function frame() {
  const items = MENU.filter((m) => allowed(m.perm));
  document.getElementById("root").innerHTML = `
    <div class="app" id="app">
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-header">
          <a class="brand" href="#/dashboard">
            <div class="brand-mark">K</div>
            <span>Kimia</span>
          </a>
        </div>
        <nav class="sidebar-nav" aria-label="Navigation principale">
          ${items.map((m) => `
            <a href="#/${m.id}" class="nav-item" data-nav="${m.id}">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                ${m.icon}
              </svg>
              <span>${m.label}</span>
              ${m.id === "notifications" ? `<span class="nav-badge" id="badge" hidden></span>` : ""}
              ${m.id === "chat" ? `<span class="nav-badge" id="chat-badge" hidden></span>` : ""}
            </a>
          `).join("")}
        </nav>
        <div class="sidebar-footer">
          <div class="user-card">
            <div class="user-avatar">${ui.initials(user.name)}</div>
            <div class="user-info">
              <div class="user-name">${ui.esc(user.name)}</div>
              <div class="user-role">${ui.esc(user.role.name)}</div>
            </div>
            <button class="btn-icon" id="logout" title="Déconnexion">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                ${ICONS.logout}
              </svg>
            </button>
          </div>
        </div>
      </aside>
      <div class="sidebar-overlay" id="overlay"></div>
      <div class="main">
        <header class="topbar">
          <div class="topbar-left">
            <button class="menu-toggle" id="menu-toggle">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                ${ICONS.menu}
              </svg>
            </button>
            <h1 class="topbar-title" id="topbar-title">Tableau de bord</h1>
          </div>
          <div class="topbar-right">
            <div class="status-pill" id="status-pill">
              <span class="status-dot"></span>
              <span id="status-text">Connexion…</span>
            </div>
          </div>
        </header>
        <div id="offline" class="offline" hidden>
          Vous êtes hors connexion. Les données affichées peuvent être périmées.
        </div>
        <main class="content" id="view" tabindex="-1"></main>
      </div>
    </div>`;

  view = document.getElementById("view");
  const app = document.getElementById("app");

  document.getElementById("menu-toggle").onclick = () => {
    document.getElementById("sidebar").classList.toggle("open");
    document.getElementById("overlay").classList.toggle("open");
  };
  document.getElementById("overlay").onclick = () => {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("overlay").classList.remove("open");
  };
  document.getElementById("logout").onclick = () => {
    session.clear();
    location.replace("login.html");
  };
  view.addEventListener("click", (e) => {
    if (e.target.closest("[data-retry]")) load(true);
  });
}

/* Status */
function paintStatus() {
  const s = store.get();
  const pill = document.getElementById("status-pill");
  const txt = document.getElementById("status-text");
  const offline = document.getElementById("offline");
  if (!pill || !txt || !offline) return;

  const mode = !s.online ? "off" : s.ws === "open" ? "on" : "wait";
  pill.className = "status-pill " + mode;
  txt.textContent = mode === "on" ? "En direct" : mode === "wait" ? "Connexion…" : "Hors ligne";
  offline.hidden = s.online;

  const badge = document.getElementById("badge");
  if (badge) {
    badge.hidden = !s.unread;
    badge.textContent = s.unread > 99 ? "99+" : s.unread;
  }
  const chatBadge = document.getElementById("chat-badge");
  if (chatBadge) {
    chatBadge.hidden = !s.unreadMessages;
    chatBadge.textContent = s.unreadMessages > 99 ? "99+" : s.unreadMessages;
  }
}

/* Route */
function parseHash() {
  const [path, q = ""] = location.hash.replace(/^#\/?/, "").split("?");
  return {
    id: path || "dashboard",
    query: Object.fromEntries(new URLSearchParams(q)),
  };
}

const ctx = () => ({
  user,
  query: current?.query || {},
  api,
  ui,
  reload: () => load(false),
  navigate: (hash) => { location.hash = hash; },
});

async function route() {
  const { id, query } = parseHash();
  const entry = MENU.find((m) => m.id === id) || MENU[0];

  document.getElementById("app").classList.remove("nav-open");
  document.querySelectorAll("[data-nav]").forEach((a) =>
    a.classList.toggle("active", a.dataset.nav === entry.id)
  );

  document.getElementById("topbar-title").textContent = entry.label;
  document.title = `${entry.label} — Kimia`;

  if (!allowed(entry.perm)) {
    current = null;
    view.innerHTML = ui.stateHTML.denied();
    return;
  }

  try {
    const mod = (await import(`../assets/js/pages/${entry.id}.js`)).default;
    current = { mod, id: entry.id, query };
    await load(true);
  } catch (e) {
    console.error(e);
    view.innerHTML = ui.stateHTML.error("Page introuvable ou en cours de développement.");
  }
}

async function load(first) {
  if (!current) return;
  const token = ++loadToken;
  const { mod } = current;

  if (first) view.innerHTML = ui.stateHTML.loading();

  try {
    const data = await mod.fetch(ctx());
    if (token !== loadToken) return;
    const y = window.scrollY;
    view.innerHTML = mod.render(data, ctx());
    if (mod.bind) mod.bind(view, data, ctx());

    requestAnimationFrame(() => {
      void view.offsetHeight;
      if (!first) window.scrollTo(0, y);
      else view.focus({ preventScroll: true });
    });
  } catch (e) {
    if (token !== loadToken) return;
    if (first) view.innerHTML = ui.stateHTML.error(e.message);
  }
}

/* Realtime */
async function refreshUnread(announce) {
  try {
    const list = await api.get("/api/notifications", { unread_only: true });
    const before = store.get().unread;
    store.set({ unread: list.length });
    if (announce && list.length > before) {
      const newest = list.reduce((a, b) => (b.id > a.id ? b : a));
      ui.toast(newest.title);
    }
  } catch {}
}

function onRealtime(evt) {
  if (evt.type === "notification.created") refreshUnread(true);
  if (evt.type === "resync") refreshUnread(false);

  // Chat : incrémenter le compteur si on n'est pas sur la page chat
  if (evt.type === "message.created") {
    const onChat = current?.id === "chat";
    if (!onChat) {
      const s = store.get();
      store.set({ unreadMessages: s.unreadMessages + 1 });
    }
  }

  const wanted =
    evt.type === "resync" ||
    evt.type === "poll" ||
    (current && (current.mod.events || []).includes(evt.type));

  if (!wanted) return;
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(() => load(false), 250);
}

/* Boot */
export async function boot() {
  if (!session.token || !session.user) {
    location.replace("login.html");
    return;
  }

  user = session.user;
  frame();
  store.subscribe(paintStatus);
  store.set({ user });
  paintStatus();

  api.get("/api/auth/me")
    .then((me) => {
      session.saveUser(me);
      user = me;
    })
    .catch(() => {});

  refreshUnread(false);
  onEvent(onRealtime);
  connect();
  addEventListener("hashchange", route);
  route();

  if (
    "serviceWorker" in navigator &&
    !["localhost", "127.0.0.1"].includes(location.hostname)
  ) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }
}