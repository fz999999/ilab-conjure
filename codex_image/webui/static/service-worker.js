const CACHE_NAME = "ilab-conjure-shell-v113";
const APP_SHELL_URLS = [
  "/",
  "/history",
  "/manifest.webmanifest",
  "/static/styles.css?v=runtime-645",
  "/static/app.js?v=runtime-645",
  "/static/history.js?v=history-71",
  "/static/pwa.js?v=pwa-2",
  "/static/brand/dachuan-logo-64.png",
  "/static/brand/dachuan-logo-180.png",
  "/static/brand/pwa-icon-192.png",
  "/static/brand/pwa-icon-512.png"
];
const APP_SHELL_PATHS = new Set(APP_SHELL_URLS.map((url) => new URL(url, self.location.origin).pathname));

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request, { ignoreSearch: true });
    if (cached) return cached;
    throw error;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const requestUrl = new URL(request.url);
  if (requestUrl.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request));
    return;
  }

  if (!APP_SHELL_PATHS.has(requestUrl.pathname)) return;

  event.respondWith(networkFirst(request));
});
