from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

# HEAD PWA
if 'manifest.webmanifest' not in s:
    s=s.replace('<meta name="format-detection" content="telephone=no">', '<meta name="format-detection" content="telephone=no">\n<link rel="manifest" href="./manifest.webmanifest">\n<link rel="icon" type="image/svg+xml" href="./icons/john-sistemas-192.svg">\n<link rel="apple-touch-icon" href="./icons/john-sistemas-192.svg">\n<meta name="application-name" content="John Sistemas">')

# Versão
s=s.replace('John Sistemas - Gestão de Empréstimos V9.2','John Sistemas - Gestão de Empréstimos V9.3')
s=s.replace('Gestão de Empréstimos • V9.2','Gestão de Empréstimos • V9.3')
s=s.replace("const APP_VERSION='9.2'", "const APP_VERSION='9.3'")
s=s.replace('const APP_VERSION = \'9.2\'', 'const APP_VERSION = \'9.3\'')

# Usa o ícone real também na tela inicial
old_logo='''    <div class="welcome-logo" aria-label="Logo John Sistemas">\n      <div class="welcome-logo-mark"><span>J</span><span>S</span></div>\n    </div>'''
new_logo='''    <div class="welcome-logo" aria-label="Logo John Sistemas">\n      <img src="./icons/john-sistemas-512.svg" alt="John Sistemas" class="welcome-logo-img">\n    </div>'''
if old_logo in s:
    s=s.replace(old_logo,new_logo)

# Botão de instalação
anchor='''    <button class="welcome-enter" onclick="openLogin()">Acessar sistema</button>'''
install='''    <button class="welcome-enter" onclick="openLogin()">Acessar sistema</button>\n    <button id="installAppBtn" class="welcome-install hidden" onclick="installPWA()">📲 Instalar no celular</button>'''
if 'id="installAppBtn"' not in s:
    s=s.replace(anchor,install)

# CSS da logo e instalação
css='''
.welcome-logo{overflow:hidden;padding:0;background:#07152d!important}
.welcome-logo-img{width:100%;height:100%;display:block;object-fit:cover;border-radius:inherit}
.welcome-install{
  width:100%;margin-top:11px;border:1px solid rgba(255,255,255,.32);border-radius:15px;padding:13px 18px;
  background:rgba(255,255,255,.09);color:#fff;font-weight:800;font-size:14px;
  box-shadow:0 10px 24px rgba(0,0,0,.14);backdrop-filter:blur(8px)
}
.welcome-install:hover{background:rgba(255,255,255,.16);transform:translateY(-1px)}
'''
if '.welcome-install{' not in s:
    s=s.replace('\n</style>','\n'+css+'\n</style>',1)

# JS PWA
pwa_js='''
<script>
let deferredInstallPrompt=null;

window.addEventListener('beforeinstallprompt',event=>{
  event.preventDefault();
  deferredInstallPrompt=event;
  const btn=document.getElementById('installAppBtn');
  if(btn) btn.classList.remove('hidden');
});

async function installPWA(){
  if(!deferredInstallPrompt){
    if(window.matchMedia('(display-mode: standalone)').matches){
      toast('O John Sistemas já está instalado neste celular.');
    }else{
      toast('No menu do navegador, escolha “Adicionar à tela inicial” ou “Instalar aplicativo”.');
    }
    return;
  }
  deferredInstallPrompt.prompt();
  const choice=await deferredInstallPrompt.userChoice;
  if(choice.outcome==='accepted'){
    const btn=document.getElementById('installAppBtn');
    if(btn) btn.classList.add('hidden');
  }
  deferredInstallPrompt=null;
}

window.addEventListener('appinstalled',()=>{
  const btn=document.getElementById('installAppBtn');
  if(btn) btn.classList.add('hidden');
  deferredInstallPrompt=null;
});

if('serviceWorker' in navigator){
  window.addEventListener('load',()=>{
    navigator.serviceWorker.register('./sw.js').catch(err=>console.warn('Service worker:',err));
  });
}

// Quando aberto pelo ícone instalado, entra direto no fluxo do sistema.
window.addEventListener('load',()=>{
  const standalone=window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone===true;
  if(standalone && typeof openLogin==='function'){
    const welcome=document.getElementById('welcomeView');
    const login=document.getElementById('loginView');
    const app=document.getElementById('appView');
    if(welcome && !welcome.classList.contains('hidden') && (!app || app.classList.contains('hidden'))){
      openLogin();
    }
  }
});
</script>
'''
if 'deferredInstallPrompt' not in s:
    s=s.replace('</body>',pwa_js+'\n</body>')

p.write_text(s,encoding='utf-8')
