/* PCP John — PWA service worker. Dados e endpoints /api nunca são armazenados. */
const VERSION = 'pcp-john-v20261015-1';
const ASSET_CACHE = 'assets-' + VERSION;
const CORE = ['/offline.html','/css/styles.css','/css/pwa.css','/js/pwa.js','/icons/pcp-john-192.png','/icons/pcp-john-512.png','/icons/pcp-john.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(ASSET_CACHE).then(cache=>cache.addAll(CORE)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(Promise.all([
    caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==ASSET_CACHE).map(key=>caches.delete(key)))),
    self.clients.claim()
  ]));
});
self.addEventListener('fetch', event => {
  const req=event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (req.mode === 'navigate') {
    event.respondWith(fetch(req,{cache:'no-store'}).catch(()=>caches.match('/offline.html')));
    return;
  }
  if (!url.pathname.startsWith('/icons/') && !url.pathname.startsWith('/css/') && !url.pathname.startsWith('/js/')) return;
  event.respondWith(fetch(req).then(response=>{
    if (response.ok) {
      const clone=response.clone();
      event.waitUntil(caches.open(ASSET_CACHE).then(cache=>cache.put(req,clone)));
    }
    return response;
  }).catch(()=>caches.match(req)));
});