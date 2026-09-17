from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

s=s.replace('<link rel="apple-touch-icon" href="./icons/john-sistemas-192.png">','<link rel="apple-touch-icon" sizes="180x180" href="./icons/john-sistemas-180.png">')
s=s.replace('John Sistemas - Gestão de Empréstimos V9.4','John Sistemas - Gestão de Empréstimos V9.5')
s=s.replace("const APP_VERSION = '9.4';","const APP_VERSION = '9.5';")
s=s.replace('Gestão de Empréstimos • V9.4','Gestão de Empréstimos • V9.5')

button='''    <button id="iosInstallBtn" class="welcome-ios-install hidden" onclick="showIOSInstallGuide()"> Adicionar ao iPhone/iPad</button>\n'''
anchor='''    <button class="welcome-enter" onclick="openLogin()">Acessar sistema</button>\n'''
if 'id="iosInstallBtn"' not in s:
    s=s.replace(anchor, anchor+button, 1)

css='''
.welcome-ios-install{
  width:100%;margin-top:11px;border:1px solid rgba(255,255,255,.34);border-radius:15px;padding:13px 18px;
  background:rgba(255,255,255,.10);color:#fff;font-weight:800;font-size:14px;
  box-shadow:0 10px 24px rgba(0,0,0,.14);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)
}
.welcome-ios-install:hover{background:rgba(255,255,255,.17);transform:translateY(-1px)}
.ios-steps{display:grid;gap:10px;margin:14px 0}
.ios-step{display:flex;gap:10px;align-items:flex-start;padding:11px 12px;border:1px solid var(--border);border-radius:12px;background:#f8fafc}
.ios-step b{display:grid;place-items:center;min-width:26px;height:26px;border-radius:50%;background:#10254d;color:#fff;font-size:12px}
'''
if '.welcome-ios-install{' not in s:
    s=s.replace('\n</style>', '\n'+css+'\n</style>', 1)

js='''
<script>
function johnIsIOS(){
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform==='MacIntel' && navigator.maxTouchPoints>1);
}
function johnIsStandalone(){
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone===true;
}
function johnIsIOSSafari(){
  const ua=navigator.userAgent;
  return johnIsIOS() && /Safari/i.test(ua) && !/(CriOS|FxiOS|EdgiOS|OPiOS|DuckDuckGo)/i.test(ua);
}
function showIOSInstallGuide(){
  if(johnIsStandalone()){
    toast('O John Sistemas já está adicionado à tela inicial.');
    return;
  }
  if(!johnIsIOSSafari()){
    modal(`
      <div class="modal-header"><h3>Instalar no iPhone / iPad</h3><button class="btn btn-outline btn-sm" onclick="closeModal()">Fechar</button></div>
      <div class="notice"><b>Abra este endereço no Safari.</b> O iOS só oferece “Adicionar à Tela de Início” pelo menu de compartilhamento do Safari.</div>
      <div class="ios-steps">
        <div class="ios-step"><b>1</b><div>Copie ou abra o endereço do John Sistemas no <strong>Safari</strong>.</div></div>
        <div class="ios-step"><b>2</b><div>No Safari, toque em <strong>Compartilhar</strong> (quadrado com seta para cima).</div></div>
        <div class="ios-step"><b>3</b><div>Escolha <strong>Adicionar à Tela de Início</strong> e depois <strong>Adicionar</strong>.</div></div>
      </div>`);
    return;
  }
  modal(`
    <div class="modal-header"><h3> Adicionar John Sistemas</h3><button class="btn btn-outline btn-sm" onclick="closeModal()">Fechar</button></div>
    <div class="notice">No iPhone/iPad a instalação é feita pelo menu do Safari.</div>
    <div class="ios-steps">
      <div class="ios-step"><b>1</b><div>Toque no botão <strong>Compartilhar</strong> do Safari — o quadrado com uma seta para cima.</div></div>
      <div class="ios-step"><b>2</b><div>Role as opções e toque em <strong>Adicionar à Tela de Início</strong>.</div></div>
      <div class="ios-step"><b>3</b><div>Confirme o nome <strong>John Sistemas</strong> e toque em <strong>Adicionar</strong>.</div></div>
      <div class="ios-step"><b>4</b><div>O ícone aparecerá na tela do iPhone/iPad. Depois, basta tocar nele para abrir o sistema como app.</div></div>
    </div>`);
}
window.addEventListener('DOMContentLoaded',()=>{
  if(johnIsIOS() && !johnIsStandalone()){
    const btn=document.getElementById('iosInstallBtn');
    if(btn) btn.classList.remove('hidden');
  }
});
if('serviceWorker' in navigator){
  window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
}
</script>
'''
if 'function johnIsIOS()' not in s:
    s=s.replace('\n</body>', '\n'+js+'\n</body>', 1)

p.write_text(s,encoding='utf-8')
