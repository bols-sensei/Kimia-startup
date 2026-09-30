/* Petit store observable : utilisateur, réseau, WebSocket, notifications non lues, messages non lus. */

const state = {
  user: null,
  online: navigator.onLine,
  ws: "closed",
  unread: 0,             // notifications non lues
  unreadMessages: 0,     // messages de chat non lus (global)
};

const subs = new Set();

export const store = {
  get: () => state,
  set(patch) {
    let changed = false;
    for (const k in patch) {
      if (state[k] !== patch[k]) {
        state[k] = patch[k];
        changed = true;
      }
    }
    if (changed) subs.forEach((fn) => fn(state));
  },
  subscribe(fn) {
    subs.add(fn);
    return () => subs.delete(fn);
  },
};

addEventListener("online", () => store.set({ online: true }));
addEventListener("offline", () => store.set({ online: false }));