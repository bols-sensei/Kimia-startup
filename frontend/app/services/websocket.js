/* WebSocket temps réel — reconnexion exponentielle, ping, resync */

import { session } from "./api.js";
import { store } from "../state/store.js";

const handlers = new Set();
let sock, timer, pingTimer, delay = 1000, hadConnection = false, started = false;

export const onEvent = (fn) => {
  handlers.add(fn);
  return () => handlers.delete(fn);
};

const emit = (evt) =>
  handlers.forEach((fn) => {
    try { fn(evt); } catch (e) { console.error(e); }
  });

function wsUrl() {
  const origin = (window.KIMIA_API || location.origin).replace(/^http/, "ws");
  return `${origin}/ws?token=${encodeURIComponent(session.token || "")}`;
}

function open() {
  clearTimeout(timer);
  store.set({ ws: "connecting" });
  sock = new WebSocket(wsUrl());

  sock.onopen = () => {
    delay = 1000;
    store.set({ ws: "open" });
    clearInterval(pingTimer);
    pingTimer = setInterval(() => sock.readyState === 1 && sock.send("ping"), 25000);
    if (hadConnection) emit({ type: "resync" });
    hadConnection = true;
  };

  sock.onmessage = (e) => {
    try { emit(JSON.parse(e.data)); } catch {}
  };

  sock.onclose = (e) => {
    clearInterval(pingTimer);
    store.set({ ws: "closed" });
    if (e.code === 4401) {
      session.clear();
      location.replace("login.html");
      return;
    }
    timer = setTimeout(open, delay);
    delay = Math.min(delay * 2, 30000);
  };

  sock.onerror = () => sock.close();
}

export function connect() {
  if (started) return;
  started = true;
  open();

  setInterval(() => {
    if (!document.hidden) emit({ type: "poll" });
  }, 90000);

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && (!sock || sock.readyState > 1)) {
      delay = 1000;
      open();
    }
  });

  addEventListener("online", () => {
    if (!sock || sock.readyState > 1) {
      delay = 1000;
      open();
    }
  });
}