/* Service Worker — précache tolérant, réseau d'abord, offline.html en fallback */

const CACHE = "kimia-app-v2";

/* Fichiers à précacher — si un fichier manque, les autres passent quand même */
const PRECACHE = [
  "index.html",
  "login.html",
  "offline.html",
  "manifest.json",
  "assets/css/app.css",
  "assets/js/main.js",
  "services/api.js",
  "services/websocket.js",
  "state/store.js",
  "utils/ui.js",
  "components/shell.js",
  "assets/icons/icon.svg",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) =>
      Promise.all(
        PRECACHE.map((url) =>
          cache.add(url).catch((err) => {
            console.warn(`[SW] Skip ${url}:`, err.message);
          })
        )
      )
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // Ne jamais intercepter : POST, autres origines, API, WebSocket, storage
  if (req.method !== "GET") return;
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  if (url.pathname.startsWith("/storage/")) return;
  if (url.pathname === "/ws") return;

  e.respondWith(
    fetch(req)
      .then((res) => {
        // Ne cacher que les réponses valides
        if (res && res.status === 200 && res.type === "basic") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => {
          if (hit) return hit;
          if (req.mode === "navigate") return caches.match("offline.html");
          return Response.error();
        })
      )
  );
}); 