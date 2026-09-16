from pathlib import Path

path = Path('index.html')
s = path.read_text(encoding='utf-8')

# Version/title
s = s.replace('<title>Jonh Sistema - Gestão de Empréstimos V9.1</title>', '<title>John Sistemas - Gestão de Empréstimos V9.2</title>')
s = s.replace('<meta name="apple-mobile-web-app-title" content="Jonh Sistema">', '<meta name="apple-mobile-web-app-title" content="John Sistemas">')
s = s.replace("const APP_VERSION = '9.1';", "const APP_VERSION = '9.2';")

# Welcome screen styles
marker = '\n</style>'
if '.welcome-wrap{' not in s:
    css = r'''

/* Tela inicial institucional - John Sistemas */
.welcome-wrap{
  min-height:100vh;
  display:grid;
  place-items:center;
  padding:28px 20px;
  position:relative;
  overflow:hidden;
  background:
    radial-gradient(circle at 20% 15%,rgba(71,118,191,.38),transparent 30%),
    radial-gradient(circle at 85% 80%,rgba(35,85,164,.28),transparent 34%),
    linear-gradient(145deg,#07152d 0%,#10254d 48%,#173a72 100%);
}
.welcome-wrap::before,.welcome-wrap::after{
  content:'';position:absolute;border:1px solid rgba(255,255,255,.09);border-radius:50%;pointer-events:none
}
.welcome-wrap::before{width:440px;height:440px;right:-170px;top:-160px}
.welcome-wrap::after{width:320px;height:320px;left:-150px;bottom:-125px}
.welcome-card{
  width:min(460px,100%);
  position:relative;z-index:1;
  text-align:center;
  padding:46px 34px 38px;
  border:1px solid rgba(255,255,255,.15);
  border-radius:30px;
  background:rgba(255,255,255,.08);
  box-shadow:0 28px 90px rgba(0,0,0,.30);
  backdrop-filter:blur(14px);
  -webkit-backdrop-filter:blur(14px);
}
.welcome-logo{
  width:112px;height:112px;margin:0 auto 24px;
  border-radius:30px;
  display:grid;place-items:center;
  color:#fff;
  background:linear-gradient(145deg,#2d68bd,#173d78);
  border:1px solid rgba(255,255,255,.30);
  box-shadow:0 18px 45px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.25);
  position:relative;
}
.welcome-logo::after{
  content:'';position:absolute;inset:9px;border:1px solid rgba(255,255,255,.18);border-radius:22px
}
.welcome-logo-mark{
  font-size:43px;font-weight:900;letter-spacing:-6px;line-height:1;
  transform:translateX(-2px)
}
.welcome-logo-mark span:last-child{opacity:.72;margin-left:3px}
.welcome-brand{
  color:#fff;font-size:29px;font-weight:900;letter-spacing:.12em;line-height:1.08
}
.welcome-brand strong{display:block;font-size:18px;letter-spacing:.28em;margin-top:8px;color:#c7d7ef}
.welcome-subtitle{margin:18px auto 30px;color:#c9d5e8;font-size:14px;line-height:1.6;max-width:320px}
.welcome-enter{
  width:100%;border:0;border-radius:15px;padding:15px 18px;
  background:#fff;color:#15366b;font-weight:850;font-size:15px;
  box-shadow:0 12px 28px rgba(0,0,0,.20);transition:.18s ease
}
.welcome-enter:hover{transform:translateY(-2px);box-shadow:0 16px 34px rgba(0,0,0,.25)}
.welcome-enter:active{transform:translateY(0)}
.welcome-version{margin-top:18px;color:rgba(255,255,255,.52);font-size:11px;letter-spacing:.08em;text-transform:uppercase}
@media(max-width:520px){
  .welcome-card{padding:38px 24px 30px;border-radius:25px}
  .welcome-logo{width:100px;height:100px;border-radius:27px}
  .welcome-brand{font-size:25px}
}
'''
    if marker not in s:
        raise SystemExit('Falha: fechamento do style não encontrado')
    s = s.replace(marker, css + marker, 1)

# Welcome markup + hide login initially
login = '<div id="loginView" class="login-wrap">'
if 'id="welcomeView"' not in s:
    welcome = r'''
<div id="welcomeView" class="welcome-wrap">
  <div class="welcome-card">
    <div class="welcome-logo" aria-label="Logo John Sistemas">
      <div class="welcome-logo-mark"><span>J</span><span>S</span></div>
    </div>
    <div class="welcome-brand">JOHN<strong>SISTEMAS</strong></div>
    <div class="welcome-subtitle">Tecnologia e gestão em um só lugar. Acesse seu ambiente de empréstimos com segurança.</div>
    <button class="welcome-enter" onclick="openLogin()">Acessar sistema</button>
    <div class="welcome-version">Gestão de Empréstimos • V9.2</div>
  </div>
</div>

'''
    if login not in s:
        raise SystemExit('Falha: tela de login não encontrada')
    s = s.replace(login, welcome + '<div id="loginView" class="login-wrap hidden">', 1)

# Navigation between welcome/login/app
anchor = 'function doLogin(){'
if 'function openLogin(){' not in s:
    fn = r'''function openLogin(){
  document.getElementById('welcomeView')?.classList.add('hidden');
  document.getElementById('loginView')?.classList.remove('hidden');
  setTimeout(()=>document.getElementById('loginUser')?.focus(),80);
}
function showWelcome(){
  document.getElementById('appView')?.classList.add('hidden');
  document.getElementById('loginView')?.classList.add('hidden');
  document.getElementById('welcomeView')?.classList.remove('hidden');
}

'''
    if anchor not in s:
        raise SystemExit('Falha: doLogin não encontrado')
    s = s.replace(anchor, fn + anchor, 1)

# enterApp must hide welcome as well
old_enter = "function enterApp(){\n  document.getElementById('loginView').classList.add('hidden');"
new_enter = "function enterApp(){\n  document.getElementById('welcomeView')?.classList.add('hidden');\n  document.getElementById('loginView').classList.add('hidden');"
if old_enter in s:
    s = s.replace(old_enter, new_enter, 1)
elif "document.getElementById('welcomeView')?.classList.add('hidden');" not in s:
    raise SystemExit('Falha: enterApp não encontrado')

# logout returns to welcome instead of login
old_logout = "  document.getElementById('appView').classList.add('hidden');\n  document.getElementById('loginView').classList.remove('hidden');"
new_logout = "  showWelcome();"
if old_logout in s:
    s = s.replace(old_logout, new_logout, 1)

# Ensure unauthenticated startup stays at welcome
old_dom = "document.addEventListener('DOMContentLoaded',()=>{\n  if(sessionStorage.getItem('jonh_auth')==='1') enterApp();"
new_dom = "document.addEventListener('DOMContentLoaded',()=>{\n  if(sessionStorage.getItem('jonh_auth')==='1') enterApp();\n  else showWelcome();"
if old_dom in s:
    s = s.replace(old_dom, new_dom, 1)
elif 'else showWelcome();' not in s:
    raise SystemExit('Falha: inicialização não encontrada')

path.write_text(s, encoding='utf-8')
print('Tela inicial John Sistemas aplicada com sucesso.')
