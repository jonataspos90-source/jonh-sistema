from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')
old = """if('serviceWorker' in navigator){
  window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
}"""
new = """if('serviceWorker' in navigator){
  let johnReloadingForSW=false;
  const johnRegisterServiceWorker=async()=>{
    try{
      const reg=await navigator.serviceWorker.register('./sw.js?v=97',{updateViaCache:'none'});
      await reg.update();
      if(reg.waiting)reg.waiting.postMessage({type:'SKIP_WAITING'});
    }catch(err){
      console.warn('Não foi possível atualizar o app PWA.',err);
    }
  };
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
    if(johnReloadingForSW)return;
    johnReloadingForSW=true;
    window.location.reload();
  });
  window.addEventListener('load',johnRegisterServiceWorker);
  window.addEventListener('pageshow',johnRegisterServiceWorker);
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='visible')johnRegisterServiceWorker();
  });
}"""
if old not in text:
    raise SystemExit('Bloco antigo de registro do service worker não encontrado.')
path.write_text(text.replace(old,new,1),encoding='utf-8')
