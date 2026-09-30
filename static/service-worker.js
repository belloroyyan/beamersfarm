const CACHE_NAME = "beamers-farm-pwa-v1";
const OFFLINE_URL = "/static/offline.html";
const PRECACHE_URLS = [
  OFFLINE_URL,
  "/manifest.webmanifest",
  "/static/css/style.css",
  "/static/js/cart.js",
  "/static/js/copy-reference.js",
  "/static/js/pwa-register.js",
  "/static/images/brand-mark.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png"
];
const PRECACHE_PATHS = new Set(PRECACHE_URLS.map((path) => new URL(path, self.location.origin).pathname));

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key.startsWith("beamers-farm-pwa-") && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never store rendered pages: order, staff, and customer data always come from the server.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(async () => {
        const cache = await caches.open(CACHE_NAME);
        return (await cache.match(OFFLINE_URL)) || new Response(
          "You appear to be offline. Reconnect and try again.",
          { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } }
        );
      })
    );
    return;
  }

  // Cache only the known public app-shell assets; do not cache uploads or API/data responses.
  if (!PRECACHE_PATHS.has(url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(url.pathname);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) await cache.put(url.pathname, response.clone());
    return response;
  })());
});
