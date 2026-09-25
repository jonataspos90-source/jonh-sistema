from pathlib import Path

index_path = Path('index.html')
sw_path = Path('sw.js')

index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')

old_registration = """if('serviceWorker' in navigator){
  window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
}"""

new_registration = """if('serviceWorker' in navigator){
  window.addEventListener('load',async()=>{
    try{
      const reg=await navigator.serviceWorker.register('./sw.js?v=97-ios-refresh',{updateViaCache:'none'});
      await reg.update();
      if(reg.waiting)reg.waiting.postMessage({type:'SKIP_WAITING'});
      reg.addEventListener('updatefound',()=>{
        const worker=reg.installing;
        if(!worker)return;
        worker.addEventListener('statechange',()=>{
          if(worker.state==='installed' && navigator.serviceWorker.controller){
            worker.postMessage({type:'SKIP_WAITING'});
          }
        });
      });
      let refreshing=false;
      navigator.serviceWorker.addEventListener('controllerchange',()=>{
        if(refreshing)return;
        refreshing=true;
        window.location.reload();
      });
    }catch(err){
      console.warn('Não foi possível atualizar o app instalado.',err);
    }
  });
}"""

if old_registration in index:
    index = index.replace(old_registration, new_registration, 1)
elif "register('./sw.js?v=97-ios-refresh'" not in index:
    raise SystemExit('Registro atual do service worker não encontrado no index.html')

sw = sw.replace("const CACHE_NAME='john-sistemas-pwa-v96';", "const CACHE_NAME='john-sistemas-pwa-v97-ios-refresh';", 1)

message_handler = """

self.addEventListener('message',event=>{
  if(event.data && event.data.type==='SKIP_WAITING')self.skipWaiting();
});
"""
if "type==='SKIP_WAITING'" not in sw:
    insert_at = sw.find("\nself.addEventListener('fetch'")
    if insert_at == -1:
        raise SystemExit('Ponto de inserção do message handler não encontrado em sw.js')
    sw = sw[:insert_at] + message_handler + sw[insert_at:]

index_path.write_text(index, encoding='utf-8')
sw_path.write_text(sw, encoding='utf-8')
print('Atualização forçada do PWA iOS aplicada: cache v97 e service worker sem cache HTTP.')
