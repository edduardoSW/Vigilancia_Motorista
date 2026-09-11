/* Service worker do DriveSafe: guarda só a casca do app (HTML, CSS, JS, fontes e ícones).
   Dados da API, tempo real, vídeo do modo teste e resultados de análise nunca vão para o cache. */

const VERSION = "drivesafe-app-0.3.0-1";

const SHELL = [
  "/",
  "/offline.html",
  "/manifest.webmanifest",
  "/assets/css/app.css",
  "/assets/js/theme.js",
  "/assets/js/app.js",
  "/assets/js/api.js",
  "/assets/js/charts.js",
  "/assets/js/config.js",
  "/assets/js/dom.js",
  "/assets/js/local/alert-types.js",
  "/assets/js/local/bus.js",
  "/assets/js/local/db.js",
  "/assets/js/local/pin.js",
  "/assets/js/local/server.js",
  "/assets/js/format.js",
  "/assets/js/live.js",
  "/assets/js/session.js",
  "/assets/js/views/account.js",
  "/assets/js/views/analyses.js",
  "/assets/js/views/companies.js",
  "/assets/js/views/company.js",
  "/assets/js/views/consents.js",
  "/assets/js/views/devices.js",
  "/assets/js/views/driver.js",
  "/assets/js/views/drivers.js",
  "/assets/js/views/fleet.js",
  "/assets/js/views/list.js",
  "/assets/js/views/login.js",
  "/assets/js/views/mypanel.js",
  "/assets/js/views/password.js",
  "/assets/js/views/reports.js",
  "/assets/js/views/review.js",
  "/assets/js/views/testmode.js",
  "/assets/js/views/users.js",
  "/assets/js/views/vehicles.js",
  "/assets/fonts/overpass-latin-wght-normal.woff2",
  "/assets/fonts/overpass-latin-ext-wght-normal.woff2",
  "/assets/fonts/overpass-mono-latin-wght-normal.woff2",
  "/assets/fonts/overpass-mono-latin-ext-wght-normal.woff2",
  "/assets/icons/icon.svg",
  "/assets/icons/icon-192.png",
  "/assets/icons/icon-512.png",
  "/assets/icons/icon-maskable-512.png",
  "/assets/icons/apple-touch-icon.png",
];

const NEVER_CACHE = [/^\/api\//, /^\/ws$/, /^\/docs/, /^\/redoc/, /^\/openapi\.json$/, /^\/health$/];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || NEVER_CACHE.some((rule) => rule.test(url.pathname))) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok && url.pathname === "/") {
            const copy = response.clone();
            caches.open(VERSION).then((cache) => cache.put("/", copy));
          }
          return response;
        })
        .catch(async () => (await caches.match("/")) || caches.match("/offline.html")),
    );
    return;
  }

  // Casca do app: responde do cache e atualiza em segundo plano.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok && response.type === "basic") {
            const copy = response.clone();
            caches.open(VERSION).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    }),
  );
});
