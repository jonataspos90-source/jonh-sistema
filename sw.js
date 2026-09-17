const CACHE_NAME='john-sistemas-pwa-v96';
const APP_SHELL=[
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/john-sistemas-180.png',
  './icons/john-sistemas-192.png',
  './icons/john-sistemas-512.png'
];

self.addEventListener('install',event=>{
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache=>cache.addAll(APP_SHELL))
      .then(()=>self.skipWaiting())
  );
});

self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.filter(k=>k.startsWith('john-sistemas-pwa') && k!==CACHE_NAME).map(k=>caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET')return;

  const url=new URL(request.url);
  if(url.origin!==self.location.origin)return;

  if(request.mode==='navigate'){
    event.respondWith((async()=>{
      try{
        const fresh=await fetch(request,{cache:'no-store'});
        const cache=await caches.open(CACHE_NAME);
        cache.put('./index.html',fresh.clone());
        return fresh;
      }catch(e){
        return (await caches.match(request)) || (await caches.match('./index.html'));
      }
    })());
    return;
  }

  event.respondWith((async()=>{
    const cached=await caches.match(request);
    if(cached)return cached;
    try{
      const fresh=await fetch(request);
      if(fresh && fresh.ok){
        const cache=await caches.open(CACHE_NAME);
        cache.put(request,fresh.clone());
      }
      return fresh;
    }catch(e){
      return cached || Response.error();
    }
  })());
});
