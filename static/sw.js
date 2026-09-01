const CACHE_NAME = "dukaanvoice-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/static/index.html",
  "/static/styles.css",
  "/static/app.js",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener("fetch", (event) => {
  // Network first fallback to cache strategy for API calls vs static assets
  if (event.request.url.includes("/api/")) {
    return; // Pass API calls through network directly
  }
  
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
