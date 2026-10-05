// Offline-Cache für die App-Dateien. Bei jeder Änderung an der App VERSION erhöhen.
const VERSION = 'kh-29';
const TILES = 'kh-tiles'; // Kartenkacheln, bleibt über Versionen hinweg erhalten
const FILES = ['./', 'index.html', 'manifest.webmanifest', 'icon-180.png', 'icon-192.png', 'icon-512.png'];
const LIBS = [
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
];
const TILE_HOSTS = ['maps1.wien.gv.at', 'tile.openstreetmap.org'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(async c => {
    await c.addAll(FILES);
    await Promise.all(LIBS.map(u => c.add(u).catch(() => {}))); // Karte ist optional, App startet auch ohne
  }).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION && k !== TILES).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  // Kartenkacheln: zuerst aus dem Cache, sonst laden und merken
  if (TILE_HOSTS.includes(url.hostname)) {
    e.respondWith(caches.open(TILES).then(async c => {
      const hit = await c.match(e.request.url);
      if (hit) return hit;
      const r = await fetch(e.request);
      c.put(e.request.url, r.clone()).catch(() => {});
      return r;
    }));
    return;
  }
  // Bibliotheken vom CDN: Cache zuerst
  if (LIBS.includes(e.request.url)) {
    e.respondWith(caches.match(e.request.url).then(r => r || fetch(e.request)));
    return;
  }
  if (url.origin !== location.origin) return; // iNaturalist-Anfragen gehen direkt ins Netz
  // App-Dateien: Netz zuerst am Browser-Cache vorbei, damit Updates sofort ankommen; ohne Empfang aus dem Cache
  e.respondWith(
    fetch(e.request, { cache: 'no-cache' }).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match('index.html')))
  );
});
