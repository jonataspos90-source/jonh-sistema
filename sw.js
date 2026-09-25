const CACHE_NAME='john-sistemas-pwa-v100-conditional-cycle-interest';
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

    const clients=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for(const client of clients){
      try{
        if(typeof client.navigate==='function')await client.navigate(client.url);
        else client.postMessage({type:'JOHN_PWA_UPDATED',cache:CACHE_NAME});
      }catch(e){
        client.postMessage({type:'JOHN_PWA_UPDATED',cache:CACHE_NAME});
      }
    }
  })());
});

self.addEventListener('message',event=>{
  if(event.data?.type==='SKIP_WAITING')self.skipWaiting();
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
    try{
      const fresh=await fetch(request,{cache:'no-store'});
      if(fresh && fresh.ok){
        const cache=await caches.open(CACHE_NAME);
        cache.put(request,fresh.clone());
      }
      return fresh;
    }catch(e){
      return (await caches.match(request)) || Response.error();
    }
  })());
});
