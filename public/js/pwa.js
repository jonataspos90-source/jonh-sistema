// PCP John — instalação segura como aplicativo web no Android e iOS.
let deferredPwaInstall = null;
const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
const installDialog = document.getElementById('pwa-install-dialog');
function syncInstallButtons(){
  document.querySelectorAll('[data-pwa-install]').forEach(button=>button.hidden=isStandalone());
}
function showInstallInstructions(){
  document.getElementById('pwa-ios').hidden=!isIOS();
  document.getElementById('pwa-android').hidden=isIOS();
  installDialog.hidden=false;
}
window.addEventListener('beforeinstallprompt',event=>{
  event.preventDefault();
  deferredPwaInstall=event;
  syncInstallButtons();
});
window.addEventListener('appinstalled',()=>{
  deferredPwaInstall=null;
  installDialog.hidden=true;
  syncInstallButtons();
});
document.addEventListener('click',async event=>{
  const install=event.target.closest('[data-pwa-install]');
  if(install){
    if(isStandalone())return;
    if(deferredPwaInstall){
      const prompt=deferredPwaInstall;deferredPwaInstall=null;
      await prompt.prompt();
      try{await prompt.userChoice;}catch{}
      syncInstallButtons();
    }else showInstallInstructions();
    return;
  }
  if(event.target.closest('[data-pwa-close]') || event.target===installDialog){installDialog.hidden=true;}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape')installDialog.hidden=true;});
window.addEventListener('DOMContentLoaded',syncInstallButtons);
syncInstallButtons();
if('serviceWorker' in navigator && window.isSecureContext){
  window.addEventListener('load',()=>{
    navigator.serviceWorker.register('/sw.js',{scope:'/',updateViaCache:'none'}).catch(error=>console.warn('PCP John: PWA indisponível:',error));
  });
}