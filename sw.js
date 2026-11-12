// Kingsrun offline support. Version changes whenever any app file changes.
const CACHE = 'kingsrun-04333b2a5a';
const ASSETS = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "maskable-512.png", "apple-touch-icon.png", "young-serif-400.woff2", "figtree-400.woff2", "figtree-500.woff2", "figtree-600.woff2", "figtree-700.woff2", "ibm-plex-mono-500.woff2"];

self.addEventListener('install', e => {
  // cache: 'reload' skips the browser's own cache, so a new version stores the new files, not stale copies
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS.map(u => new Request(u, {cache: 'reload'})))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('krmotion-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (req.mode === 'navigate') {
    // Network first so a new version shows up when online; fall back to the cached game offline.
    e.respondWith(
      // no-cache: always ask the server whether the page changed, so an update shows on the next open
      fetch(req, {cache: 'no-cache'}).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put('index.html', copy));
        return res;
      }).catch(() => caches.match('index.html', {ignoreSearch: true}))
    );
    return;
  }
  e.respondWith(caches.match(req, {ignoreSearch: true}).then(hit => hit || fetch(req)));
});
