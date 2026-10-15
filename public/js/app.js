// John Sistemas · Frontend sem bundler. API e autorização são as únicas fontes de verdade.
const state={token:sessionStorage.getItem('john_token'),user:null,initialized:false,tab:'dashboard',products:[],recipes:[],balances:[],movements:[],dashboard:{},reports:{},users:[],productQuery:'',typeFilter:'',kardexProduct:'',stockView:'balances',abcMetric:'revenue',reportStart:'',reportEnd:'',sensitivity:10,recipeDraft:[]};
const $=(sel,root=document)=>root.querySelector(sel);
const $$=(sel,root=document)=>[...root.querySelectorAll(sel)];
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=x=>Number(x)||0;
const nfmt=(x,d=2)=>new Intl.NumberFormat('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(num(x));
const money=x=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(num(x));
const dt=x=>x?new Date(x).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—';
const role=x=>({admin:'Administrador',operator:'Operador',viewer:'Consulta'}[x]||x);
const pBy=id=>state.products.find(p=>String(p.id)===String(id));
const rBy=id=>state.recipes.find(r=>String(r.productId)===String(id));
const editable=()=>state.user?.role!=='viewer';
const admin=()=>state.user?.role==='admin';
function toast(message,error=false){const t=document.createElement('div');t.className=`toast${error?' error':''}`;t.textContent=message;$('#toasts').append(t);setTimeout(()=>t.remove(),4800);}
async function api(path,{method='GET',body}={}){
 const resp=await fetch('/api'+path,{method,headers:{...(body?{'Content-Type':'application/json'}:{}),...(state.token?{Authorization:'Bearer '+state.token}:{})},...(body?{body:JSON.stringify(body)}:{})});
 let data;try{data=await resp.json();}catch{data={};}
 if(!resp.ok){if([401,403].includes(resp.status)&&resp.status===401&&state.user){logout(false);toast('Sua sessão expirou. Entre novamente.',true);}throw Error(data.error||`Erro HTTP ${resp.status}`);}
 return data;
}
async function attempt(fn){try{await fn();}catch(e){console.error(e);toast(e.message||'Falha na operação.',true);}}
function logout(show=true){sessionStorage.removeItem('john_token');state.token=null;state.user=null;$('#app').hidden=true;$('#auth-screen').hidden=false;closeModal();if(show)toast('Sessão encerrada.');}
async function start(){
 $('#today').textContent=new Intl.DateTimeFormat('pt-BR',{dateStyle:'long'}).format(new Date());
 try{const s=await api('/auth/status');state.initialized=s.initialized;}catch(e){toast('Não foi possível conectar à API. Verifique o servidor.',true);}
 showAuth();
 if(state.token)await attempt(async()=>{state.user=await api('/auth/me');await enter();});
}
function showAuth(){const first=!state.initialized;$('#auth-title').textContent=first?'Configure seu ambiente':'Bem-vindo de volta';$('#auth-subtitle').textContent=first?'Cadastre o primeiro administrador do John Sistemas.':'Entre com seu e-mail e senha para continuar.';$('#bootstrap-name-field').hidden=!first;$('#bootstrap-name-field input').required=first;$('#bootstrap-key-field').hidden=!first;$('#bootstrap-key-field input').required=first;$('#password-hint').hidden=!first;$('#auth-submit').firstChild.textContent=first?'Criar administrador ':'Acessar painel ';$('#auth-form input[name=password]').autocomplete=first?'new-password':'current-password';}
$('#auth-form').addEventListener('submit',e=>{e.preventDefault();attempt(async()=>{
 const fd=new FormData(e.currentTarget),first=!state.initialized;
 const body={email:fd.get('email'),password:fd.get('password')};if(first){body.name=fd.get('name');body.bootstrapSecret=fd.get('bootstrapSecret');}
 const result=await api(first?'/auth/bootstrap':'/auth/login',{method:'POST',body});
 state.token=result.token;sessionStorage.setItem('john_token',state.token);state.user=result.user;state.initialized=true;await enter();toast(first?'Administrador criado com sucesso.':'Bem-vindo ao John Sistemas!');
 });});
$('#logout-btn').addEventListener('click',()=>logout());
$('#menu-toggle').addEventListener('click',()=>$('#sidebar').classList.toggle('show'));
async function enter(){
 $('#auth-screen').hidden=true;$('#app').hidden=false;
 $('#user-name').textContent=state.user.name;$('#user-role').textContent=role(state.user.role);
 $('#user-avatar').textContent=state.user.name.split(' ').slice(0,2).map(x=>x[0]).join('').toUpperCase();
 $('#nav-users').hidden=!admin();await refreshAll();goTab('dashboard');
}
async function refreshAll(){
 const [products,recipes,balances,movements,dashboard]=await Promise.all([api('/products'),api('/recipes'),api('/stock/balances'),api('/stock/movements'),api('/reports/dashboard')]);
 Object.assign(state,{products,recipes,balances,movements,dashboard});$('#nav-products-count').textContent=products.length;
}
const titles={dashboard:'Visão geral',products:'Base de produtos',recipes:'Fichas técnicas',stock:'Estoque & Kardex',reports:'Relatórios gerenciais',users:'Usuários & Acessos'};
function goTab(tab){
 if(tab==='users'&&!admin())return;
 state.tab=tab;$$('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
 $('#page-title').textContent=titles[tab];$('#breadcrumb-current').textContent=titles[tab].toUpperCase();
 $('#sidebar').classList.remove('show');render();
}
$('#sidebar-nav').addEventListener('click',e=>{const button=e.target.closest('[data-tab]');if(button)goTab(button.dataset.tab);});
function render(){
 const views={dashboard:dashboardView,products:productsView,recipes:recipesView,stock:stockView,reports:reportsView,users:usersView};
 $('#view').innerHTML=(views[state.tab]||dashboardView)();
 $$('[data-pct]', $('#view')).forEach(el=>{el.style.width=el.dataset.pct+'%';});
}
function hero(kicker,title,sub,actions=''){return `<div class="page-intro"><div><span class="eyebrow">${kicker}</span><h2>${title}</h2><p>${sub}</p></div><div class="actions">${actions}</div></div>`;}
function button(text,act,variant='primary',id=''){return `<button type="button" class="btn ${variant}" data-act="${act}" ${id?`data-id="${esc(id)}"`:''}>${text}</button>`;}
function badge(label,type='neutral'){return `<span class="badge ${type}">${esc(label)}</span>`;}
function noData(txt='Nenhum registro encontrado.'){return `<div class="empty"><strong>Nada por aqui</strong>${esc(txt)}</div>`;}
function flagBadges(types){return (types||[]).map(t=>badge(t,t==='Produto Acabado'?'success':t==='Subproduto'?'warn':'neutral')).join('');}
function actionBtns(p,kind='product'){
 if(!editable())return '—';
 return `<div class="table-actions"><button class="btn tiny ghost" data-act="edit-${kind}" data-id="${esc(p.id??p.productId)}">Editar</button>${admin()?`<button class="btn tiny danger" data-act="delete-${kind}" data-id="${esc(p.id??p.productId)}">Excluir</button>`:''}</div>`;
}
function dashboardView(){const d=state.dashboard;
 const cards=[['PRODUTOS CADASTRADOS',d.totalProducts||0,'Itens na base de produtos','▣'],['FICHAS TÉCNICAS',d.totalRecipes||0,'Composições cadastradas','▤'],['VALOR DO ESTOQUE',money(d.stockValue),'Valorização pelo custo médio','◈'],['CUSTOS DESATUALIZADOS',d.staleCosts||0,'Sem atualização há mais de 30 dias','◷']];
 return `<div class="page-intro"><div><span class="eyebrow">PAINEL DE CONTROLE · TEMPO REAL</span><h2>Olá, ${esc(state.user.name.split(' ')[0])} <span class="green">↗</span></h2><p>Acompanhe os números que movem a sua operação.</p></div><div class="actions">${editable()?button('＋ Novo produto','new-product'):''}${editable()?button('＋ Nova ficha técnica','new-recipe','blue-btn'):''}</div></div>
 <div class="cards">${cards.map(([name,value,help,icon])=>`<div class="card kpi"><span class="kpi-icon">${icon}</span><div class="kpi-label">${name}</div><div class="kpi-value mono">${value}</div><div class="kpi-help">${help}</div></div>`).join('')}</div>
 <div class="dashboard-grid"><div><section class="illustrated-hero"><div class="line-grid">J</div><div class="eyebrow">INTELIGÊNCIA DE PRODUÇÃO</div><h2>Seu resultado começa<br>pelo custo certo.</h2><p>Converta insumos, calcule perdas, componha fichas e controle a produção sem comprometer sua margem.</p><div class="spaced">${button('Explorar fichas técnicas →','goto-recipes')}</div></section>
 <section class="surface spaced"><div class="section-heading"><h3>Atalhos de operação</h3><small>ACESSO RÁPIDO</small></div><div class="actions">${editable()?`${button('⇧ Entrada de compra','purchase','ghost')}${button('◈ Produzir lote','production','ghost')}${button('⇩ Registrar venda','sale','ghost')}`:''}${button('▥ Relatórios','goto-reports','ghost')}</div></section></div>
 <section class="surface"><div class="section-heading"><h3>Alertas de operação</h3><small>${(d.lowStock||[]).length+(d.belowMargin||[]).length} ALERTAS</small></div>${[...(d.lowStock||[]).slice(0,5).map(p=>`<div class="alert-row"><span class="alert-icon">!</span><div><strong>${esc(p.name)}</strong><small>Saldo ${nfmt(p.stock,3)} ${esc(p.base_unit)} · mínimo ${nfmt(p.min_stock,3)}</small></div>${badge('Baixo estoque','danger')}</div>`),...(d.belowMargin||[]).slice(0,5).map(r=>`<div class="alert-row"><span class="alert-icon">↘</span><div><strong>${esc(r.productName)}</strong><small>Margem praticada ${nfmt(r.contributionPct)}% · meta ${nfmt(r.targetMargin)}%</small></div>${badge('Margem baixa','warn')}</div>`)].join('')||noData('Nenhuma ruptura ou margem abaixo da meta.')}
 <div class="metric-line spaced"><span>Subprodutos cadastrados</span><strong>${d.subproducts||0}</strong></div><div class="metric-line"><span>Valor total do estoque</span><strong class="green">${money(d.stockValue)}</strong></div></section></div>`;
}
function productsView(){const flags=['Produto Acabado','Revenda','Embalagem','Uso e Consumo','Subproduto','Insumo'];
 const products=state.products.filter(p=>p.name.toLowerCase().includes(state.productQuery.toLowerCase())&&(!state.typeFilter||p.types.includes(state.typeFilter)));
 return hero('CATÁLOGO & INSUMOS','Sua base de produtos','Compra, embalagem, conversão, fator de correção e estoque em um cadastro único.',editable()?button('＋ Cadastrar produto','new-product'):'')+`
 <div class="toolbar"><div class="filter-row"><input class="search" id="product-search" placeholder="⌕ Buscar pelo nome do produto..." value="${esc(state.productQuery)}"><select class="select" id="product-type-filter"><option value="">Todas as classificações</option>${flags.map(x=>`<option ${state.typeFilter===x?'selected':''}>${x}</option>`).join('')}</select></div><small class="muted">${products.length} de ${state.products.length} produtos</small></div>
 <div class="table-wrap"><table><thead><tr><th>Produto</th><th>Classificação</th><th>Compra / Conteúdo</th><th>Custo real por base</th><th>Fator de correção</th><th>Saldo atual</th><th>Preço praticado</th><th class="text-right">Ações</th></tr></thead><tbody>${products.map(p=>{const base=p.theoreticalCost==null?null:num(p.theoreticalCost);return `<tr><td><span class="td-title">${esc(p.name)}</span><span class="td-caption">Código #${p.id} · ${esc(p.base_unit)}</span></td><td>${flagBadges(p.types)}</td><td><strong>${money(p.purchase_price)}</strong><span class="td-caption">${nfmt(p.package_qty,3)} ${esc(p.package_unit)} / ${esc(p.purchase_unit)}</span></td><td class="mono">${base===null?'Inconsistente':money(base)} / ${esc(p.base_unit)}<span class="td-caption">Compra: ${money(p.costBase)} / ${esc(p.base_unit)} · Custo médio: ${money(p.avg_cost)}</span></td><td>${nfmt(p.fc,3)}×</td><td><strong class="${p.lowStock?'red':'green'}">${nfmt(p.stock,3)} ${esc(p.base_unit)}</strong>${p.lowStock?'<span class="td-caption red">Abaixo do mínimo</span>':''}</td><td>${p.practiced_price==null?'—':money(p.practiced_price)}</td><td>${actionBtns(p)}</td></tr>`;}).join('')||`<tr><td colspan="8">${noData()}</td></tr>`}</tbody></table></div>`;
}
function recipesView(){return hero('CUSTO DE PRODUÇÃO','Fichas técnicas & receitas','Custos proporcionais, subprodutos encadeados, FC e precificação por margem real ou markup.',editable()?button('＋ Nova ficha técnica','new-recipe'):'')+`<div class="recipe-grid">${state.recipes.map(r=>{
 if(r.error)return `<section class="surface recipe-card"><h3>${esc(r.productId)}</h3><p class="red">${esc(r.error)}</p></section>`;
 return `<article class="surface recipe-card"><div class="recipe-head"><div><span class="eyebrow">FICHA #${r.id}</span><h3>${esc(r.productName)}</h3></div>${badge(r.belowTarget?'Margem em alerta':'Precificada',r.belowTarget?'warn':'success')}</div><div class="recipe-meta">Rendimento: <strong>${nfmt(r.yieldQty,3)} ${esc(r.baseUnit)}</strong><br>Ingredientes: <strong>${r.items.length}</strong> · Precificação: ${r.pricingMode==='margin'?'Margem de contribuição':'Markup'} (${nfmt(r.margin)}%)</div><div class="recipe-mini"><div><small>Custo por ${esc(r.baseUnit)}</small><strong>${money(r.unitCost)}</strong></div><div><small>Venda sugerida</small><strong class="green">${money(r.suggestedPrice)}</strong></div></div><div class="metric-line spaced"><span>Custo total do lote</span><strong>${money(r.totalCost)}</strong></div><div class="metric-line"><span>Preço praticado</span><strong>${money(r.practicedPrice)}</strong></div><div class="metric-line"><span>Margem de contribuição</span><strong class="${r.belowTarget?'red':'green'}">${nfmt(r.contributionPct)}%</strong></div><div class="actions spaced">${editable()?button('Editar ficha','edit-recipe','ghost',r.productId):''}${admin()?button('Excluir ficha','delete-recipe','danger',r.productId):''}</div></article>`;
 }).join('')||noData('Cadastre um Produto Acabado ou Subproduto e crie sua primeira ficha.')}</div>`;}
function stockView(){const balances=state.balances,prodOpts=state.products.map(p=>`<option value="${p.id}" ${String(p.id)===String(state.kardexProduct)?'selected':''}>${esc(p.name)}</option>`).join('');
 return hero('MOVIMENTAÇÕES & AUDITORIA','Estoque em tempo real','Registre entradas, vendas, produção, perdas e inventários. O Kardex preserva todas as alterações.',editable()?`${button('⇧ Compra','purchase')}${button('◈ Produção','production','blue-btn')}${button('＋ Outras movimentações','stock-menu','ghost')}`:'')+`
 <div class="toolbar"><div class="filter-pills"><button class="filter-pill ${state.stockView==='balances'?'active':''}" data-act="show-balances">Saldos atuais</button><button class="filter-pill ${state.stockView==='movements'?'active':''}" data-act="show-movements">Histórico Kardex</button></div>${state.stockView==='movements'?`<select class="select" id="kardex-product"><option value="">Todos os produtos</option>${prodOpts}</select>`:''}</div>
 ${state.stockView==='balances'?`<div class="table-wrap"><table><thead><tr><th>Produto</th><th>Classificação</th><th>Saldo físico</th><th>Estoque mínimo</th><th>Custo médio</th><th>Valoração</th><th>Status</th></tr></thead><tbody>${balances.map(p=>`<tr><td class="td-title">${esc(p.name)}</td><td>${flagBadges(p.types)}</td><td class="mono"><strong>${nfmt(p.stock,3)}</strong> ${esc(p.base_unit)}</td><td>${nfmt(p.min_stock,3)} ${esc(p.base_unit)}</td><td>${money(p.avg_cost)}</td><td class="green">${money(p.stock_value)}</td><td>${p.low_stock?badge('Repor estoque','danger'):badge('Normal','success')}</td></tr>`).join('')||`<tr><td colspan="7">${noData()}</td></tr>`}</tbody></table></div>`:
 `<div class="table-wrap"><table><thead><tr><th>Data & hora</th><th>Produto</th><th>Movimentação</th><th>Anterior</th><th>Variação</th><th>Saldo final</th><th>Operador / motivo</th></tr></thead><tbody>${state.movements.filter(m=>!state.kardexProduct||String(m.product_id)===String(state.kardexProduct)).map(m=>`<tr><td class="nowrap">${dt(m.created_at)}</td><td><span class="td-title">${esc(m.product_name)}</span><span class="td-caption">Lote ${esc(String(m.batch_id).slice(0,8))}</span></td><td>${badge(kinds[m.kind]||m.kind,num(m.delta)>0?'success':'warn')}</td><td>${nfmt(m.before_qty,3)}</td><td class="mono ${num(m.delta)>0?'green':'red'}">${num(m.delta)>0?'+':''}${nfmt(m.delta,3)} ${esc(m.base_unit)}</td><td><strong>${nfmt(m.after_qty,3)}</strong></td><td>${esc(m.actor_name||'Sistema')}<span class="td-caption">${esc(m.reason||'—')}</span></td></tr>`).join('')||`<tr><td colspan="7">${noData()}</td></tr>`}</tbody></table></div>`}`;
}
const kinds={purchase:'Compra / recebimento',sale:'Venda',internal:'Saída interna',adjust:'Ajuste de inventário',loss:'Perda / baixa',production_in:'Produção (entrada)',production_out:'Produção (consumo)'};
function reportsView(){const r=state.reports;
 if(!r.valuation)return hero('INTELIGÊNCIA GERENCIAL','Relatórios & indicadores','Analise margem, curva ABC, valor de estoque e sensibilidade de insumos.')+noData('Carregando relatórios...');
 const abc=r.abc||{items:[],metric:'inventory',total:0},rows=r.margins||[],val=r.valuation||{total:0,items:[]};
 return hero('BUSINESS INTELLIGENCE','Relatórios & indicadores','Curva ABC, posição financeira de estoque e lucratividade de cada receita.',button('↻ Atualizar','refresh-reports','ghost'))+`
 <div class="stats-inline"><div><small>Estoque valorizado</small><strong class="green">${money(val.total)}</strong></div><div><small>Itens na Curva ABC</small><strong>${abc.items.length}</strong></div><div><small>Fichas abaixo da margem</small><strong class="${rows.some(x=>x.belowTarget)?'red':'green'}">${rows.filter(x=>x.belowTarget).length}</strong></div></div>
 <div class="report-grid spaced"><section class="surface"><div class="section-heading"><h3>Curva ABC de produtos</h3>${badge(abc.metric==='inventory'?'Por valor em estoque':abc.metric==='cost'?'Por custo de vendas':'Por faturamento','neutral')}</div>
 <div class="toolbar"><select id="abc-metric" class="select"><option value="revenue" ${state.abcMetric==='revenue'?'selected':''}>Faturamento</option><option value="cost" ${state.abcMetric==='cost'?'selected':''}>Custo das vendas</option></select><div class="filter-row"><input class="input date-input" id="report-start" type="date" value="${esc(state.reportStart)}" title="Início"><input class="input date-input" id="report-end" type="date" value="${esc(state.reportEnd)}" title="Fim">${button('Aplicar','filter-reports','ghost')}</div></div>
 ${abc.items.slice(0,10).map(x=>`<div class="abc-row"><div><div class="section-heading compact-heading"><strong>${esc(x.name)}</strong>${badge('Classe '+x.class,x.class==='A'?'success':x.class==='B'?'warn':'neutral')}</div><div class="legend-bar"><div class="legend-fill" data-pct="${Math.min(100,Math.max(0,num(x.cumulative)))}"></div></div><small>Acumulado: ${nfmt(x.cumulative)}% · Participação: ${nfmt(x.share)}%</small></div><strong class="text-right mono">${money(x.value)}</strong></div>`).join('')||noData('Sem vendas ou estoque valorizado no período.')}
 <p class="chart-caption">A ≈ primeiros 80%, B ≈ 15% seguintes, C ≈ 5% finais. Itens que cruzam o limite são atribuídos à classe em que iniciam. Sem vendas no período, a métrica muda explicitamente para valor em estoque.</p></section>
 <section class="surface"><div class="section-heading"><h3>Rentabilidade & cenários</h3>${badge('Simulação +'+nfmt(state.sensitivity,0)+'%','neutral')}</div>
 <div class="field"><label>Aumento uniforme hipotético do custo dos ingredientes (%)</label><div class="filter-row"><input class="input small-input" id="sensitivity" type="number" min="0" max="100" value="${state.sensitivity}">${button('Simular','simulate','ghost')}</div></div>
 ${(r.sensitivity||[]).slice(0,9).map(x=>x.error?'':`<div class="metric-line"><span>${esc(x.name)}<small class="td-caption">Custo: ${money(x.currentCost)} → ${money(x.costAfter)}</small></span><strong class="green">${money(x.priceNow)} → ${money(x.priceAfter)}</strong></div>`).join('')||noData('Crie fichas técnicas para simular.')}
 <p class="chart-caption">Cenário uniforme hipotético: todos os custos de ingredientes sobem ${nfmt(state.sensitivity,0)}%. Não altera preços ou saldos reais.</p></section></div>
 <section class="surface spaced"><div class="section-heading"><h3>Margens de contribuição por produto</h3><small>COMPARATIVO PREÇO / CUSTO</small></div><div class="table-wrap"><table><thead><tr><th>Produto</th><th>Rendimento</th><th>Custo unitário</th><th>Venda sugerida</th><th>Preço praticado</th><th>Contribuição R$</th><th>Margem %</th><th>Situação</th></tr></thead><tbody>${rows.map(x=>x.error?`<tr><td colspan="8" class="red">${esc(x.error)}</td></tr>`:`<tr><td class="td-title">${esc(x.productName)}</td><td>${nfmt(x.yieldQty,3)} ${esc(x.baseUnit)}</td><td>${money(x.unitCost)}</td><td>${money(x.suggestedPrice)}</td><td>${money(x.practicedPrice)}</td><td class="${num(x.contributionAmount)<0?'red':'green'}">${money(x.contributionAmount)}</td><td><strong class="${x.belowTarget?'red':'green'}">${nfmt(x.contributionPct)}%</strong></td><td>${badge(x.belowTarget?'Abaixo da meta':'Dentro da meta',x.belowTarget?'danger':'success')}</td></tr>`).join('')||`<tr><td colspan="8">${noData()}</td></tr>`}</tbody></table></div><p class="chart-caption">Margem de contribuição aqui considera custos diretos dos ingredientes/embalagens; não inclui automaticamente impostos, comissões, fretes ou despesas fixas. Configure o preço praticado no produto.</p></section>
 <section class="surface spaced"><div class="section-heading"><h3>Valoração de estoque pelo custo médio ponderado</h3><span class="green">${money(val.total)}</span></div><div class="table-wrap"><table><thead><tr><th>Produto</th><th>Saldo físico</th><th>Custo médio</th><th>Valor em estoque</th></tr></thead><tbody>${val.items.filter(x=>num(x.stock)>0).map(x=>`<tr><td class="td-title">${esc(x.name)}</td><td>${nfmt(x.stock,3)} ${esc(x.base_unit)}</td><td>${money(x.avg_cost)}</td><td class="green mono">${money(x.value)}</td></tr>`).join('')||`<tr><td colspan="4">${noData()}</td></tr>`}</tbody></table></div></section>`;
}
function usersView(){if(!admin())return noData('Acesso restrito aos administradores.');return hero('ADMINISTRAÇÃO','Usuários & permissões','Controle quem pode gerenciar o sistema, registrar operações ou apenas consultar.',button('＋ Novo usuário','new-user'))+
 `<div class="table-wrap"><table><thead><tr><th>Colaborador</th><th>E-mail</th><th>Perfil</th><th>Situação</th><th>Desde</th><th class="text-right">Ações</th></tr></thead><tbody>${state.users.map(u=>`<tr><td class="td-title">${esc(u.name)}</td><td>${esc(u.email)}</td><td>${badge(role(u.role))}</td><td>${badge(u.active?'Ativo':'Inativo',u.active?'success':'danger')}</td><td>${dt(u.created_at)}</td><td class="text-right">${button('Editar acesso','edit-user','ghost',u.id)}</td></tr>`).join('')||`<tr><td colspan="6">${noData()}</td></tr>`}</tbody></table></div>`;}
async function loadReports(){const [valuation,margins,abc,sensitivity]=await Promise.all([api('/reports/valuation'),api('/reports/margins'),api(`/reports/abc?metric=${state.abcMetric}&start=${state.reportStart}&end=${state.reportEnd}`),api(`/reports/sensitivity?change=${state.sensitivity}`)]);state.reports={valuation,margins,abc,sensitivity};}
function openModal(title,body,{kind='generic',narrow=false,submit='Salvar'}={}){
 $('#modal-root').innerHTML=`<div class="modal-backdrop" id="overlay"><section class="modal ${narrow?'narrow':''}" role="dialog" aria-modal="true"><div class="modal-header"><div><span class="eyebrow">JOHN SISTEMAS · OPERAÇÃO</span><h3>${esc(title)}</h3></div><button class="icon-btn" type="button" data-act="close-modal" aria-label="Fechar">✕</button></div><form id="dialog-form" data-kind="${kind}"><div class="modal-body">${body}</div></form><div class="modal-footer"><button class="btn ghost" data-act="close-modal">Cancelar</button><button class="btn primary" type="submit" form="dialog-form">${esc(submit)} →</button></div></section></div>`;
}
function closeModal(){$('#modal-root').innerHTML='';state.recipeDraft=[];}
function field(name,label,type='text',value='',options={}){return `<div class="field"><label for="f-${name}">${label}</label><input id="f-${name}" name="${name}" type="${type}" value="${esc(value??'')}" ${options.step?`step="${options.step}"`:''} ${options.min!==undefined?`min="${options.min}"`:''} ${options.max!==undefined?`max="${options.max}"`:''} ${options.placeholder?`placeholder="${esc(options.placeholder)}"`:''} ${options.required===false?'':'required'}></div>`;}
function selectField(name,label,opts,current){return `<div class="field"><label for="f-${name}">${label}</label><select id="f-${name}" name="${name}">${opts.map(o=>{const [value,text]=Array.isArray(o)?o:[o,o];return `<option value="${esc(value)}" ${String(current)===String(value)?'selected':''}>${esc(text)}</option>`;}).join('')}</select></div>`;}
const units=['mg','g','kg','ml','l','un'];
function baseUnit(unit){return ['mg','g','kg'].includes(unit)?'kg':['ml','l'].includes(unit)?'l':'un';}
function baseQuantity(q,u){return num(q)/({mg:1000000,g:1000,ml:1000}[u]||1);}
function productCost(p){return num(p.avg_cost)>0?num(p.avg_cost):baseQuantity(p.package_qty,p.package_unit)>0?num(p.purchase_price)/baseQuantity(p.package_qty,p.package_unit):0;}
function productModal(p=null){
 const types=['Produto Acabado','Revenda','Embalagem','Uso e Consumo','Subproduto','Insumo'];
 openModal(p?'Editar produto':'Cadastrar produto',`<input type="hidden" name="id" value="${p?.id||''}">
 ${field('name','Nome do produto','text',p?.name||'',{placeholder:'Ex: Margarina Doriana 500g'})}
 <div class="form-block"><h4>CLASSIFICAÇÕES MÚLTIPLAS</h4><div class="checks">${types.map(t=>`<label class="check"><input type="checkbox" name="types" value="${esc(t)}" ${(p?.types||['Insumo']).includes(t)?'checked':''}>${esc(t)}</label>`).join('')}</div></div>
 <div class="form-grid three">${selectField('purchaseUnit','Embalagem de compra',['pacote','pote','frasco','caixa','saco','unidade','kg','litro'],p?.purchase_unit||'pacote')}${field('packageQty','Conteúdo da embalagem','number',p?.package_qty??500,{min:.000001,step:'any'})}${selectField('packageUnit','Unidade do conteúdo',units,p?.package_unit||'g')}</div>
 <div class="form-grid">${field('purchasePrice','Preço de compra da embalagem (R$)','number',p?.purchase_price??0,{min:0,step:'any'})}${field('minStock','Estoque mínimo na unidade base','number',p?.min_stock??0,{min:0,step:'any'})}</div>
 <div class="form-grid">${field('practicedPrice','Preço de venda praticado (R$), opcional','number',p?.practiced_price??'',{required:false,min:0,step:'any'})}${field('fc','Fator de correção (FC ≥ 1)','number',p?.fc??1,{min:1,step:'any'})}</div>
 <div class="form-block"><h4>TESTE DE RENDIMENTO / PRÉ-PREPARO (OPCIONAL)</h4><p class="muted micro-copy">Informe peso bruto e líquido na MESMA unidade. O FC será calculado como PB ÷ PL. Sem teste, digite o FC acima.</p><div class="form-grid">${field('testGross','Peso bruto do teste','number',p?.test_gross??'',{required:false,min:.000001,step:'any'})}${field('testNet','Peso líquido aproveitável','number',p?.test_net??'',{required:false,min:.000001,step:'any'})}</div></div>
 <div class="calculator"><div><small>Unidade padrão e volume convertido</small><strong id="product-base-preview">—</strong></div><div><small>Custo real corrigido / unidade base</small><strong id="product-cost-preview">—</strong></div></div>
 <div class="form-note">O estoque não é alterado no cadastro. Faça entrada por compra ou ajuste inicial justificado para garantir o Kardex. Estoque sempre em kg, L ou un (não em embalagens).</div>
 `,{kind:'product',submit:p?'Atualizar produto':'Cadastrar produto'});
 updateProductPreview();
}
function updateProductPreview(){
 const f=$('#dialog-form');if(!f||f.dataset.kind!=='product')return;
 const q=num(f.elements.packageQty.value),u=f.elements.packageUnit.value,p=num(f.elements.purchasePrice.value);
 const gross=num(f.elements.testGross.value),net=num(f.elements.testNet.value);
 if(gross>0&&net>0&&gross>=net){f.elements.fc.value=(gross/net).toFixed(6);}
 const base=baseQuantity(q,u),fc=num(f.elements.fc.value);
 $('#product-base-preview').textContent=`${nfmt(base,4)} ${baseUnit(u)}`;
 $('#product-cost-preview').textContent=base>0&&fc>=1?`${money((p/base)*fc)} / ${baseUnit(u)}`:'Verifique conteúdo / FC';
}
async function saveProduct(f){
 const fd=new FormData(f),types=fd.getAll('types');
 const payload={name:fd.get('name'),types,purchaseUnit:fd.get('purchaseUnit'),packageQty:num(fd.get('packageQty')),packageUnit:fd.get('packageUnit'),purchasePrice:num(fd.get('purchasePrice')),fc:num(fd.get('fc')),minStock:num(fd.get('minStock')),practicedPrice:fd.get('practicedPrice')===''?null:num(fd.get('practicedPrice')),testGross:fd.get('testGross')===''?null:num(fd.get('testGross')),testNet:fd.get('testNet')===''?null:num(fd.get('testNet'))};
 if(!types.length)throw Error('Marque pelo menos uma classificação.');
 if(payload.testGross!==null||payload.testNet!==null){if(!payload.testGross||!payload.testNet||payload.testGross<payload.testNet)throw Error('Para o teste, informe PB e PL válidos (PB ≥ PL).');}
 if(baseUnit(payload.packageUnit)==='un'&&payload.fc!==1)throw Error('FC para unidades deve ser 1 nesta versão.');
 const id=fd.get('id');await api(id?'/products/'+id:'/products',{method:id?'PUT':'POST',body:payload});closeModal();await refreshAll();render();toast(id?'Produto atualizado.':'Produto cadastrado.');
}
function recipeModal(productId=null){
 const eligible=state.products.filter(p=>p.types.some(t=>['Produto Acabado','Subproduto'].includes(t)));
 if(!eligible.length){toast('Cadastre um Produto Acabado ou Subproduto primeiro.',true);return;}
 const cur=productId?rBy(productId):null;
 const output=cur?String(cur.productId):String(eligible[0].id);
 state.recipeDraft=cur?cur.items.map(i=>({productId:String(i.productId),netQty:num(i.netQty)})):[];
 const options=eligible.map(p=>[p.id,`${p.name} (${p.base_unit})`]);
 openModal(cur?'Editar ficha técnica':'Nova ficha técnica',`
 ${selectField('productId','Produto final / subproduto',options,output)}
 <div class="form-grid three">${field('yieldQty','Rendimento final (unidade base)','number',cur?.yieldQty??1,{min:.000001,step:'any'})}${field('margin','Percentual desejado (%)','number',cur?.margin??30,{min:0,max:99.99,step:'any'})}${selectField('pricingMode','Modo de precificação',[['margin','Margem de contribuição'],['markup','Markup sobre custo']],cur?.pricingMode||'margin')}</div>
 <div class="form-note" id="recipe-yield-label">Informe o rendimento em ${esc(pBy(output)?.base_unit||'un')}. Quantidades de insumos são sempre informadas em kg, L ou un, já após limpeza (líquidas).</div>
 <div class="form-block"><div class="section-heading"><h4 class="no-margin">INGREDIENTES, EMBALAGENS & SUBPRODUTOS</h4>${button('＋ Ingrediente','add-ingredient','ghost')}</div><div id="ingredient-container"></div></div>
 <div class="calculator"><div><small>Custo estimado do lote</small><strong id="recipe-total-preview">R$ 0,00</strong></div><div><small>Preço sugerido / unidade de rendimento</small><strong id="recipe-price-preview">R$ 0,00</strong></div></div>
 <div class="form-note">Margem de contribuição: preço = custo ÷ (1 − margem/100). Markup: preço = custo × (1 + percentual/100). Subprodutos entram pelo custo teórico de sua ficha técnica.</div>
 `,{kind:'recipe',submit:'Salvar ficha técnica'});
 renderIngredients();
}
function costIngredient(p,seen=new Set()){
 if(!p)return 0;
 if(seen.has(String(p.id)))return 0;
 if(p.theoreticalCost!==null&&p.theoreticalCost!==undefined)return num(p.theoreticalCost);
 const r=rBy(p.id);if(r&&!r.error)return num(r.unitCost)*num(p.fc);
 return productCost(p)*num(p.fc);
}
function renderIngredients(){
 const f=$('#dialog-form');if(!f||f.dataset.kind!=='recipe')return;
 const output=f.elements.productId.value;
 const ingredients=state.products.filter(p=>String(p.id)!==String(output));
 $('#ingredient-container').innerHTML=state.recipeDraft.map((item,idx)=>{
 const chosen=pBy(item.productId)||ingredients[0];
 if(!item.productId&&chosen)item.productId=String(chosen.id);
 return `<div class="ingredient-row"><div class="field"><label>Insumo / embalagem</label><select data-item-field="productId" data-index="${idx}">${ingredients.map(p=>`<option value="${p.id}" ${String(p.id)===String(item.productId)?'selected':''}>${esc(p.name)} (${esc(p.base_unit)})</option>`).join('')}</select></div><div class="field"><label>Qtd. líquida</label><input type="number" data-item-field="netQty" data-index="${idx}" step="any" min="0.000001" value="${esc(item.netQty)}"><small>Em ${esc(chosen?.base_unit||'un')}</small></div><div class="subtotal field"><label>Custo da porção</label><span class="recipe-subtotal">${money(costIngredient(pBy(item.productId))*num(item.netQty))}</span><small>FC: ${nfmt(chosen?.fc??1,3)}×</small></div><button class="btn danger tiny" type="button" data-act="remove-ingredient" data-index="${idx}">✕</button></div>`;
 }).join('')||'<p class="empty-copy">Nenhum ingrediente. Clique em “+ Ingrediente”.</p>';
 $('#recipe-yield-label').textContent=`Rendimento informado em ${pBy(output)?.base_unit||'un'}. Cada ingrediente deve ser informado em sua unidade de cálculo (kg/L/un), considerando o peso líquido aproveitável.`;
 recipePreview();
}
function recipePreview(){const f=$('#dialog-form');if(!f||f.dataset.kind!=='recipe')return;
 const total=state.recipeDraft.reduce((sum,i)=>sum+costIngredient(pBy(i.productId))*num(i.netQty),0);
 const unit=total/Math.max(num(f.elements.yieldQty.value),1e-15);
 const margin=num(f.elements.margin.value)/100,price=f.elements.pricingMode.value==='markup'?unit*(1+margin):margin<1?unit/(1-margin):0;
 $('#recipe-total-preview').textContent=money(total);$('#recipe-price-preview').textContent=money(price);
}
async function saveRecipe(f){
 const fd=new FormData(f),productId=num(fd.get('productId'));
 if(!state.recipeDraft.length)throw Error('Adicione pelo menos um ingrediente à ficha.');
 const items=state.recipeDraft.map(i=>({productId:num(i.productId),netQty:num(i.netQty)}));
 if(items.some(i=>!i.productId||i.netQty<=0))throw Error('Preencha produto e quantidade positiva em todos os ingredientes.');
 const body={productId,yieldQty:num(fd.get('yieldQty')),margin:num(fd.get('margin')),pricingMode:fd.get('pricingMode'),items};
 await api('/recipes',{method:'POST',body});closeModal();await refreshAll();render();toast('Ficha técnica salva com sucesso.');
}
function stockModal(kind='purchase',id=null){
 const prods=kind==='production'?state.products.filter(p=>rBy(p.id)):kind==='sale'?state.products.filter(p=>p.types.some(t=>['Produto Acabado','Revenda','Subproduto'].includes(t))):state.products;
 if(!prods.length){toast('Nenhum produto elegível para a operação.',true);return;}
 const opts=prods.map(p=>[p.id,`${p.name} (${p.base_unit})`]);
 let content=`${selectField('productId','Produto',opts,id??prods[0].id)}`;
 if(kind==='purchase')content+=`<div class="form-grid">${field('packages','Quantidade de embalagens compradas','number',1,{min:.000001,step:'any'})}${field('purchasePrice','Preço POR EMBALAGEM (R$)','number',pBy(id??prods[0].id)?.purchase_price??0,{min:0,step:'any'})}</div><div class="form-note" id="stock-preview">O volume será convertido automaticamente à unidade base do produto.</div>`;
 if(kind==='production')content+=`${field('outputQty','Quantidade produzida (unidade base)','number',1,{min:.000001,step:'any'})}<div class="form-note" id="stock-preview">O sistema fará a baixa proporcional de todos os ingredientes, validará saldos e dará entrada no produto final, em uma única transação.</div>`;
 if(kind==='sale'||kind==='internal')content+=`<div class="form-grid">${field('quantity','Quantidade retirada (unidade base)','number',1,{min:.000001,step:'any'})}${kind==='sale'?field('unitPrice','Preço praticado por unidade base (R$)','number',pBy(id??prods[0].id)?.practiced_price??0,{min:0,step:'any'}):''}</div>`;
 if(kind==='adjust'||kind==='loss')content+=`${field('delta','Variação no saldo (ex: -2 ou +3)','number',0,{step:'any'})}<div class="form-note">Ajustes são obrigatoriamente justificados e auditados. Para perdas e quebras, informe uma quantidade negativa.</div>`;
 if(kind!=='purchase')content+=`<div class="field"><label>Motivo / observação ${kind==='adjust'||kind==='loss'||kind==='internal'?'(obrigatório)':'(opcional)'}</label><textarea name="reason" maxlength="500" ${kind==='adjust'||kind==='loss'||kind==='internal'?'required':''} placeholder="Ex: contagem física, produção de lote, validade vencida..."></textarea></div>`;
 else content+=`<div class="field"><label>Observação da compra (opcional)</label><textarea name="reason" placeholder="Fornecedor / nota fiscal / lote"></textarea></div>`;
 openModal(({purchase:'Entrada por compra',production:'Ordem de produção',sale:'Saída por venda',internal:'Saída para uso interno',adjust:'Ajuste de inventário',loss:'Perda / quebra'})[kind],`<input type="hidden" name="kind" value="${kind}">${content}`,{kind:'stock',narrow:true,submit:'Confirmar movimentação'});
 stockPreview();
}
function stockPreview(){const f=$('#dialog-form');if(!f||f.dataset.kind!=='stock')return;
 const kind=f.elements.kind.value,p=pBy(f.elements.productId.value),target=$('#stock-preview');if(!target||!p)return;
 if(kind==='purchase'){const packs=num(f.elements.packages.value),qty=baseQuantity(p.package_qty,p.package_unit)*packs;target.textContent=`Recebimento: ${nfmt(packs,3)} embalagens → +${nfmt(qty,4)} ${p.base_unit} no estoque. Total da compra: ${money(packs*num(f.elements.purchasePrice.value))}. O custo médio será recalculado.`;}
 if(kind==='production'){const r=rBy(p.id),qty=num(f.elements.outputQty.value),multiple=r?qty/num(r.yieldQty):0;
 target.innerHTML=r?`<b>Produção: +${nfmt(qty,3)} ${esc(p.base_unit)}</b><br>Fator do lote: ${nfmt(multiple,4)}×<br>${r.items.map(i=>{const ing=pBy(i.productId);return `${esc(ing?.name)}: −${nfmt(num(i.netQty)*num(ing?.fc??1)*multiple,4)} ${esc(ing?.base_unit||'un')}`;}).join('<br>')}`:'Produto sem ficha técnica.';
 }
}
async function saveStock(f){const fd=new FormData(f),kind=fd.get('kind'),productId=num(fd.get('productId'));let path,body;
 if(kind==='purchase'){path='/stock/purchase';body={productId,packages:num(fd.get('packages')),purchasePrice:num(fd.get('purchasePrice')),reason:fd.get('reason')};}
 if(kind==='production'){path='/stock/production';body={productId,outputQty:num(fd.get('outputQty')),reason:fd.get('reason')};}
 if(kind==='sale'||kind==='internal'){path='/stock/sale';body={productId,quantity:num(fd.get('quantity')),type:kind,reason:fd.get('reason')};if(kind==='sale')body.unitPrice=num(fd.get('unitPrice'));}
 if(kind==='adjust'||kind==='loss'){path='/stock/adjust';body={productId,delta:num(fd.get('delta')),reason:fd.get('reason'),kind};}
 const result=await api(path,{method:'POST',body});closeModal();await refreshAll();render();toast(`Movimentação registrada${result.batchId?' · lote '+String(result.batchId).slice(0,8):''}.`);
}
function userModal(user=null){if(!admin())return;
 openModal(user?'Editar usuário / acesso':'Cadastrar novo usuário',`<input type="hidden" name="id" value="${user?.id||''}">
 ${field('name','Nome completo','text',user?.name||'')}${user?'':field('email','E-mail','email','')}
 <div class="form-grid">${selectField('role','Perfil de acesso',[['admin','Administrador'],['operator','Operador'],['viewer','Consulta']],user?.role||'operator')}${user?selectField('active','Situação',[['true','Ativo'],['false','Inativo']],String(user.active)):'<div class="form-note">Administrador: gerencia usuários e exclui registros. Operador: cadastra e movimenta. Consulta: apenas leitura.</div>'}</div>
 ${field('password',user?'Nova senha (deixe em branco para manter)':'Senha inicial (mínimo 10 caracteres)','password','',{required:!user,placeholder:'Mínimo 10 caracteres'})}
 `,{kind:'user',narrow:true,submit:'Salvar acesso'});
}
async function saveUser(f){const fd=new FormData(f),id=fd.get('id');const body={name:fd.get('name'),role:fd.get('role')};if(id){body.active=fd.get('active')==='true';if(fd.get('password'))body.password=fd.get('password');}
 else{body.email=fd.get('email');body.password=fd.get('password');}
 await api(id?'/auth/users/'+id:'/auth/users',{method:id?'PATCH':'POST',body});closeModal();state.users=await api('/auth/users');render();toast('Usuário salvo.');
}
async function confirmDelete(kind,id){
 const product=pBy(id),r=rBy(id);
 const label=kind==='product'?product?.name:r?.productName;
 if(!window.confirm(`Confirma ${kind==='product'?'o arquivamento do produto':'a exclusão da ficha técnica'} "${label}"? Esta ação não altera registros históricos.`))return;
 await api(kind==='product'?'/products/'+id:'/recipes/'+id,{method:'DELETE'});await refreshAll();render();toast('Operação concluída.');
}
// Delegação mantém todos os botões funcionais após atualizações de tela.
document.addEventListener('click',e=>{const b=e.target.closest('[data-act]');if(!b)return;
 const action=b.dataset.act,id=b.dataset.id;
 if(action==='close-modal'){closeModal();return;}
 attempt(async()=>{
 switch(action){
 case 'new-product':productModal();break;
 case 'edit-product':productModal(pBy(id));break;
 case 'delete-product':await confirmDelete('product',id);break;
 case 'new-recipe':recipeModal();break;
 case 'edit-recipe':recipeModal(id);break;
 case 'delete-recipe':await confirmDelete('recipe',id);break;
 case 'add-ingredient':{
 const f=$('#dialog-form');const p=state.products.find(p=>String(p.id)!==String(f.elements.productId.value));if(!p)throw Error('Cadastre outro produto para usar como ingrediente.');
 state.recipeDraft.push({productId:String(p.id),netQty:1});renderIngredients();break;
 }
 case 'remove-ingredient':state.recipeDraft.splice(Number(b.dataset.index),1);renderIngredients();break;
 case 'purchase':case 'production':case 'sale':case 'internal':case 'adjust':case 'loss':stockModal(action,id);break;
 case 'stock-menu':stockMenu();break;
 case 'show-balances':state.stockView='balances';render();break;
 case 'show-movements':state.stockView='movements';render();break;
 case 'goto-recipes':goTab('recipes');break;
 case 'goto-reports':await loadReports();goTab('reports');break;
 case 'refresh-reports':await loadReports();render();toast('Indicadores atualizados.');break;
 case 'filter-reports':state.abcMetric=$('#abc-metric').value;state.reportStart=$('#report-start').value;state.reportEnd=$('#report-end').value;await loadReports();render();break;
 case 'simulate':state.sensitivity=Math.min(100,Math.max(0,num($('#sensitivity').value)));await loadReports();render();break;
 case 'new-user':userModal();break;
 case 'edit-user':userModal(state.users.find(u=>String(u.id)===String(id)));break;
 }
 });
});
function stockMenu(){openModal('Escolha a movimentação',`<div class="actions">${button('⇩ Venda de produto','sale','ghost')}${button('↘ Saída interna','internal','ghost')}${button('≋ Ajuste de inventário','adjust','ghost')}${button('⚠ Perda / quebra','loss','danger')}${button('⇧ Entrada de compra','purchase','ghost')}${button('◈ Ordem de produção','production','ghost')}</div><div class="form-note">Perdas e quebras são registradas com ajuste negativo e justificativa obrigatória.</div>`,{kind:'none',narrow:true,submit:'Fechar'});}
document.addEventListener('submit',e=>{const f=e.target;if(f.id!=='dialog-form')return;e.preventDefault();const submit=$('[type=submit][form=dialog-form]');if(submit)submit.disabled=true;
 attempt(async()=>{try{switch(f.dataset.kind){case 'product':await saveProduct(f);break;case 'recipe':await saveRecipe(f);break;case 'stock':await saveStock(f);break;case 'user':await saveUser(f);break;default:closeModal();}}finally{if(submit?.isConnected)submit.disabled=false;}});
});
// Busca instantânea com posição do cursor preservada (atualiza só a tabela).
document.addEventListener('input',e=>{
 if(e.target.id==='product-search'){
  state.productQuery=e.target.value;
  const selection=e.target.selectionStart;
  render();const newField=$('#product-search');newField?.focus();if(newField)newField.setSelectionRange(selection,selection);return;
 }
 const f=$('#dialog-form');if(!f)return;
 if(f.dataset.kind==='product'&&['packageQty','packageUnit','purchasePrice','fc','testGross','testNet'].includes(e.target.name))updateProductPreview();
 if(f.dataset.kind==='recipe'&&['yieldQty','margin','pricingMode'].includes(e.target.name))recipePreview();
 if(f.dataset.kind==='stock'&&['packages','purchasePrice','outputQty'].includes(e.target.name))stockPreview();
 if(f.dataset.kind==='recipe'&&e.target.matches('[data-item-field]')){
  const row=state.recipeDraft[Number(e.target.dataset.index)];row[e.target.dataset.itemField]=e.target.dataset.itemField==='netQty'?num(e.target.value):e.target.value;
  if(e.target.tagName==='SELECT')renderIngredients();else{recipePreview();const parent=e.target.closest('.ingredient-row');const ing=pBy(row.productId);parent.querySelector('.recipe-subtotal').textContent=money(costIngredient(ing)*num(row.netQty));}
 }
});
document.addEventListener('change',e=>{
 if(e.target.id==='product-type-filter'){state.typeFilter=e.target.value;render();}
 if(e.target.id==='kardex-product'){state.kardexProduct=e.target.value;render();}
 const f=$('#dialog-form');if(f?.dataset.kind==='recipe'&&e.target.name==='productId')renderIngredients();
 if(f?.dataset.kind==='stock'&&e.target.name==='productId'){
  if(f.elements.kind.value==='purchase')f.elements.purchasePrice.value=pBy(e.target.value)?.purchase_price??0;
  if(f.elements.kind.value==='sale')f.elements.unitPrice.value=pBy(e.target.value)?.practiced_price??0;
  stockPreview();
 }
 if(f?.dataset.kind==='product'&&e.target.name==='packageUnit')updateProductPreview();
});
// Carrega dados de módulos gerenciais apenas ao abri-los.
// A navegação é interceptada na própria função de eventos, sem relógios/polling.
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-tab]');if(!b)return;
 if(b.dataset.tab==='reports')attempt(async()=>{await loadReports();if(state.tab==='reports')render();});
 if(b.dataset.tab==='users')attempt(async()=>{state.users=await api('/auth/users');if(state.tab==='users')render();});
});
start();
