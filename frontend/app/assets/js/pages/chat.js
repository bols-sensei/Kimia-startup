import * as ui from "../../../utils/ui.js";
import { store } from "../../../state/store.js";
const { esc, fmtDateTime, pageHead, toast } = ui;

/* État local */
let currentChannelId = null;
let channels = [];
let messages = [];
let lastMessageId = 0;
let pollTimer = null;

/* Icônes */
const HASH_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg>';
const SEND_ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';

export default {
  title: "Chat",
  roles: null,
  events: ["message.created", "message.updated", "message.deleted"],

  async fetch({ api, query }) {
    // Charger les canaux
    channels = await api.get("/api/chat/channels");

    if (!channels.length) {
      return { channels: [], messages: [], currentChannelId: null };
    }

    // Déterminer le canal à ouvrir
    let wanted = query.channel ? Number(query.channel) : null;
    if (!wanted || !channels.find((c) => c.id === wanted)) {
      wanted = currentChannelId && channels.find((c) => c.id === currentChannelId)
        ? currentChannelId
        : channels[0].id;
    }
    currentChannelId = wanted;

    // Charger les messages
    messages = await api.get(`/api/chat/channels/${currentChannelId}/messages`, { limit: 100 });
    lastMessageId = messages.length ? Math.max(...messages.map((m) => m.id)) : 0;

    // Marquer comme lu
    await api.post(`/api/chat/channels/${currentChannelId}/read`).catch(() => {});
    // Reset du compteur global
    store.set({ unreadMessages: 0 });

    return { channels, messages, currentChannelId };
  },

  render({ channels, messages, currentChannelId }) {
    if (!channels.length) {
      return pageHead("Chat") + ui.stateHTML.empty(
        "Aucun canal",
        "Le canal #général devrait apparaître automatiquement."
      );
    }

    const current = channels.find((c) => c.id === currentChannelId);

    return pageHead("Chat", `${channels.length} canal${channels.length > 1 ? "x" : ""}`) + `
      <div class="chat-layout">
        <aside class="chat-sidebar">
          <div class="chat-sidebar-header">
            <h2>Canaux</h2>
          </div>
          <div class="chat-channels">
            ${channels.map((c) => renderChannelItem(c, currentChannelId)).join("")}
          </div>
        </aside>

        <section class="chat-main">
          <header class="chat-main-header">
            <div class="chat-channel-title">
              <span class="chat-channel-icon">${HASH_ICON}</span>
              <h3>${esc(current?.name || "Canal")}</h3>
              ${current?.type === "PROJECT" ? `<span class="tag">Projet</span>` : ""}
            </div>
          </header>

          <div class="chat-messages" id="chat-messages">
            ${renderMessages(messages)}
          </div>

          <form class="chat-input" id="chat-form">
            <textarea
              id="chat-textarea"
              placeholder="Tapez un message…"
              rows="1"
              autocomplete="off"
            ></textarea>
            <button type="submit" class="chat-send" title="Envoyer">
              ${SEND_ICON}
            </button>
          </form>
        </section>
      </div>
    `;
  },

  bind(view, data, { api, reload, user }) {
    const messagesEl = view.querySelector("#chat-messages");
    const form = view.querySelector("#chat-form");
    const textarea = view.querySelector("#chat-textarea");

    // Scroll bas
    const scrollToBottom = () => {
      if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
    };
    scrollToBottom();

    // Auto-resize du textarea
    const autoResize = () => {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 140) + "px";
    };
    textarea?.addEventListener("input", autoResize);

    // Envoyer avec Entrée, retour à la ligne avec Shift+Entrée
    textarea?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });

    // Changement de canal
    view.querySelectorAll("[data-channel]").forEach((el) => {
      el.addEventListener("click", () => {
        const id = Number(el.dataset.channel);
        if (id === currentChannelId) return;
        currentChannelId = id;
        reload();
      });
    });

    // Envoi du message
    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const content = textarea.value.trim();
      if (!content) return;

      textarea.value = "";
      autoResize();

      try {
        await api.post(`/api/chat/channels/${currentChannelId}/messages`, { content });
        // Le WebSocket va déclencher le reload
      } catch (err) {
        toast(err.message || "Erreur d'envoi", "error");
      }
    });

    // Suppression d'un message
    view.querySelectorAll("[data-delete]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = Number(btn.dataset.delete);
        if (!confirm("Supprimer ce message ?")) return;
        try {
          await api.del(`/api/chat/messages/${id}`);
          toast("Message supprimé");
          reload();
        } catch (err) {
          toast(err.message || "Erreur", "error");
        }
      });
    });

    // Polling de secours toutes les 15s
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      if (!currentChannelId) return;
      try {
        const newMessages = await api.get(
          `/api/chat/channels/${currentChannelId}/messages`,
          { limit: 100, before_id: undefined }
        );
        const newLastId = newMessages.length ? Math.max(...newMessages.map((m) => m.id)) : 0;
        if (newLastId > lastMessageId) {
          lastMessageId = newLastId;
          reload();
        }
      } catch {}
    }, 15000);

    // Nettoyer le timer quand on quitte la page
    window.addEventListener("hashchange", () => clearInterval(pollTimer), { once: true });
  },
};


/* --------------------------------------------------------------------------- */
/* Rendu : canal dans la sidebar */
/* --------------------------------------------------------------------------- */

function renderChannelItem(channel, currentId) {
  const isActive = channel.id === currentId;
  const unread = channel.unread_count || 0;

  return `
    <button class="chat-channel ${isActive ? "active" : ""}" data-channel="${channel.id}">
      <span class="chat-channel-hash">${HASH_ICON}</span>
      <span class="chat-channel-name">${esc(channel.name)}</span>
      ${unread > 0 ? `<span class="chat-channel-badge">${unread > 99 ? "99+" : unread}</span>` : ""}
    </button>
  `;
}


/* --------------------------------------------------------------------------- */
/* Rendu : messages */
/* --------------------------------------------------------------------------- */

function renderMessages(messages) {
  if (!messages.length) {
    return `
      <div class="chat-empty">
        <div class="chat-empty-icon">${HASH_ICON}</div>
        <div class="chat-empty-title">Aucun message</div>
        <div class="chat-empty-text">Soyez le premier à écrire.</div>
      </div>
    `;
  }

  const user = store.get().user;
  let lastDate = "";
  const parts = [];

  for (const m of messages) {
    // Séparateur de date
    const d = new Date(m.created_at);
    const dayKey = d.toDateString();
    if (dayKey !== lastDate) {
      lastDate = dayKey;
      parts.push(`
        <div class="chat-date-separator">
          <span>${formatDay(d)}</span>
        </div>
      `);
    }

    const isMe = user && m.user_id === user.id;
    const isEdited = m.edited_at && m.edited_at !== m.created_at;

    parts.push(`
      <div class="chat-message ${isMe ? "me" : ""}" data-id="${m.id}">
        ${!isMe ? `
          <div class="chat-message-avatar">${esc(m.user_initials || "?")}</div>
        ` : ""}
        <div class="chat-message-content">
          ${!isMe ? `<div class="chat-message-author">${esc(m.user_name || "Inconnu")}</div>` : ""}
          <div class="chat-message-bubble">
            ${escapeAndLinkify(m.content)}
          </div>
          <div class="chat-message-meta">
            ${formatTime(d)}
            ${isEdited ? " · modifié" : ""}
            ${isMe ? `<button class="chat-message-delete" data-delete="${m.id}" title="Supprimer">×</button>` : ""}
          </div>
        </div>
      </div>
    `);
  }

  return parts.join("");
}


/* --------------------------------------------------------------------------- */
/* Helpers */
/* --------------------------------------------------------------------------- */

function formatTime(d) {
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatDay(d) {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (d.toDateString() === today.toDateString()) return "Aujourd'hui";
  if (d.toDateString() === yesterday.toDateString()) return "Hier";

  return d.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: d.getFullYear() !== today.getFullYear() ? "numeric" : undefined,
  });
}

function escapeAndLinkify(text) {
  // Échapper
  let safe = esc(text);

  // Liens
  safe = safe.replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>'
  );

  // Sauts de ligne
  safe = safe.replace(/\n/g, "<br>");

  return safe;
}