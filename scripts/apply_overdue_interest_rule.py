from pathlib import Path
import re

path = Path('index.html')
s = path.read_text(encoding='utf-8')


def sub_once(pattern, repl, label, flags=0):
    global s
    s2, n = re.subn(pattern, repl, s, count=1, flags=flags)
    if n != 1:
        raise SystemExit(f'Falha ao aplicar {label}: encontrados {n} trechos')
    s = s2

# 1) Configuração: a regra deixa de ser percentual manual e passa a ser fixa/proporcional por dia.
s = s.replace(
    '<div class="field"><label>Multa por atraso (%)</label><input id="cfgLateFee" type="number" step="0.01"></div>',
    '<div class="field full"><label>Regra de juros por atraso</label><input id="cfgLateFee" type="text" value="Juros do contrato ÷ 30 × dias em atraso" readonly></div>'
)
s = s.replace("document.getElementById('cfgLateFee').value=s.lateFee;", "document.getElementById('cfgLateFee').value='Juros do contrato ÷ 30 × dias em atraso';")
s = s.replace("state.settings.lateFee=Number(document.getElementById('cfgLateFee').value||0);", "state.settings.lateFee=0;")

# 2) Pagamentos de atraso não reduzem o principal/juros contratuais duas vezes.
sub_once(
    r"function loanPaid\(loanId\)\{ return state\.payments\.filter\(p=>p\.loanId===loanId\)\.reduce\(\(a,b\)=>a\+Number\(b\.value\),0\); \}",
    """function paymentOverduePart(p){ return Math.max(0,Number(p?.overdueInterestPart||0)); }
function paymentContractPart(p){ return Math.max(0,Number(p?.value||0)-paymentOverduePart(p)); }
function loanPaid(loanId){ return state.payments.filter(p=>p.loanId===loanId).reduce((a,p)=>a+paymentContractPart(p),0); }
function loanOverduePaid(loanId){ return state.payments.filter(p=>p.loanId===loanId).reduce((a,p)=>a+paymentOverduePart(p),0); }""",
    'separação de pagamentos contratuais e atraso'
)

# 3) Regra central de juros em atraso.
sub_once(
    r"function loanBalance\(l\)\{\s*const renewal=latestRenewal\(l\);\s*if\(renewal\)\{\s*const paidAfter=Math\.max\(0,loanPaid\(l\.id\)-Number\(renewal\.paidTotal\|\|0\)\);\s*return Math\.max\(0,Number\(renewal\.newBalance\|\|0\)-paidAfter\);\s*\}\s*return Math\.max\(0,Number\(l\.total\)-loanPaid\(l\.id\)\);\s*\}",
    """function loanBalance(l){
  const renewal=latestRenewal(l);
  if(renewal){
    const paidAfter=Math.max(0,loanPaid(l.id)-Number(renewal.paidTotal||0));
    return Math.max(0,Number(renewal.newBalance||0)-paidAfter);
  }
  return Math.max(0,Number(l.total)-loanPaid(l.id));
}
function loanCurrentDueDate(l){
  const renewal=latestRenewal(l);
  return renewal?.dueDate || l.dueDate || '';
}
function loanInterestBaseForOverdue(l){
  const renewal=latestRenewal(l);
  if(renewal)return Math.max(0,Number(renewal.interestAdded||0));
  return Math.max(0,Number(l.total||0)-Number(l.principal||0));
}
function loanOverdueDays(l,referenceDate=todayISO()){
  const due=loanCurrentDueDate(l);
  if(!due||!referenceDate)return 0;
  const d=new Date(due+'T00:00:00');
  const r=new Date(referenceDate+'T00:00:00');
  if(Number.isNaN(d.getTime())||Number.isNaN(r.getTime()))return 0;
  return Math.max(0,Math.floor((r-d)/86400000));
}
function loanOverdueInterest(l,referenceDate=todayISO()){
  if(!l||['Cancelado','Renegociado','Excluído'].includes(l.status)||loanBalance(l)<=0.009)return 0;
  const days=loanOverdueDays(l,referenceDate);
  if(days<=0)return 0;
  const base=loanInterestBaseForOverdue(l);
  const accrued=(base/30)*days;
  return Math.max(0,accrued-loanOverduePaid(l.id));
}
function loanTotalDue(l,referenceDate=todayISO()){
  return Math.max(0,loanBalance(l)+loanOverdueInterest(l,referenceDate));
}""",
    'funções de juros em atraso',
    re.S
)

# 4) Status usa vencimento do ciclo atual e considera encargos.
sub_once(
    r"function loanStatus\(l\)\{\s*if\(\['Cancelado','Renegociado','Excluído'\]\.includes\(l\.status\)\)return l\.status;\s*const bal=loanBalance\(l\);\s*if\(bal<=0\.009\)return 'Quitado';\s*if\(new Date\(l\.dueDate\+'T23:59:59'\)<new Date\(\)\)return 'Vencido';\s*if\(loanPaid\(l\.id\)>0\)return 'Parcial';",
    """function loanStatus(l){
  if(['Cancelado','Renegociado','Excluído'].includes(l.status))return l.status;
  const bal=loanTotalDue(l);
  if(bal<=0.009)return 'Quitado';
  if(new Date(loanCurrentDueDate(l)+'T23:59:59')<new Date())return 'Vencido';
  if(loanPaid(l.id)>0)return 'Parcial';""",
    'status do contrato',
    re.S
)

# 5) DRE: juros de atraso entram como receita financeira, sem virar principal.
s = s.replace(
    "return {principal:Number(p.principalPart||0),interest:Number(p.interestPart||0)};",
    "return {principal:Number(p.principalPart||0),interest:Number(p.interestPart||0)+paymentOverduePart(p),overdueInterest:paymentOverduePart(p)};"
)

# 6) Valores exibidos no dashboard/conta/cobrança passam a considerar o atraso.
s = s.replace(
    "reduce((a,l)=>a+loanBalance(l),0);",
    "reduce((a,l)=>a+loanTotalDue(l),0);",
    1
)
s = s.replace(
    "const total=overdue.reduce((a,l)=>a+loanBalance(l),0);",
    "const total=overdue.reduce((a,l)=>a+loanTotalDue(l),0);"
)
s = s.replace(
    "const current=state.loans.filter(l=>l.clientId===clientId&&!['Cancelado','Renegociado','Excluído'].includes(l.status)).reduce((a,l)=>a+loanBalance(l),0);",
    "const current=state.loans.filter(l=>l.clientId===clientId&&!['Cancelado','Renegociado','Excluído'].includes(l.status)).reduce((a,l)=>a+loanTotalDue(l),0);"
)

# 7) Tela de cobrança: vencimento do ciclo atual e total atualizado.
sub_once(
    r"function renderCollection\(\)\{.*?\n\}\nfunction copyCollection",
    """function renderCollection(){
  const now=new Date();now.setHours(0,0,0,0); const limit=new Date(now);limit.setDate(limit.getDate()+7);
  const rows=state.loans.filter(l=>{
    const due=loanCurrentDueDate(l); const d=new Date(due+'T00:00:00');
    return loanBalance(l)>0 && !['Cancelado','Renegociado','Excluído'].includes(l.status) && d<=limit;
  }).sort((a,b)=>loanCurrentDueDate(a).localeCompare(loanCurrentDueDate(b)));
  document.getElementById('collectionTable').innerHTML=rows.length?rows.map(l=>{
    const c=state.clients.find(x=>x.id===l.clientId); const due=loanCurrentDueDate(l); const d=new Date(due+'T00:00:00');
    const diff=Math.floor((now-d)/86400000); const s=diff>0?'Vencido':diff===0?'Vence hoje':`Em ${Math.abs(diff)} dia(s)`;
    const late=loanOverdueInterest(l);
    return `<tr><td>${safe(c?.name||'-')}</td><td>#${l.contractNo}</td><td>${dateBR(due)}</td><td>${diff>0?diff+' em atraso':diff===0?'Hoje':Math.abs(diff)+' para vencer'}</td><td>${brl(loanTotalDue(l))}${late>0?`<div style=\"font-size:11px;color:var(--danger);margin-top:3px\">Inclui ${brl(late)} de juros de atraso</div>`:''}</td><td>${safe(c?.phone||'-')}</td><td>${badgeStatus(diff>0?'Vencido':s)}</td><td class=\"split\"><button class=\"btn btn-success btn-sm\" onclick=\"openPaymentModal('${l.id}')\">Receber</button><button class=\"btn btn-outline btn-sm\" onclick=\"copyCollection('${l.id}')\">Copiar cobrança</button></td></tr>`;
  }).join(''):`<tr><td colspan=\"8\" class=\"empty\">Nenhuma cobrança para os próximos 7 dias.</td></tr>`;
}
function copyCollection""",
    'tela de cobrança',
    re.S
)

sub_once(
    r"function copyCollection\(id\)\{.*?\n\}\nfunction copyLoanMessage",
    """function copyCollection(id){
  const l=state.loans.find(x=>x.id===id); const c=state.clients.find(x=>x.id===l.clientId);
  const due=loanCurrentDueDate(l); const late=loanOverdueInterest(l); const days=loanOverdueDays(l);
  const lines=[
    `Olá, ${c.name}.`,
    '',
    `Passando para lembrar sobre o contrato nº ${l.contractNo}.`,
    '',
    `Saldo contratual: ${brl(loanBalance(l))}`,
    ...(late>0?[`Juros de atraso (${days} dia(s)): ${brl(late)}`,`Total atualizado: ${brl(loanTotalDue(l))}`]:[]),
    `Vencimento: ${dateBR(due)}`,
    '',
    'Caso o pagamento já tenha sido realizado, por favor, desconsidere esta mensagem.',
    '',
    'Atenciosamente,',
    'John Sistemas'
  ];
  const msg=lines.join(String.fromCharCode(10));
  navigator.clipboard?.writeText(msg);toast('Mensagem de cobrança copiada.');
}
function copyLoanMessage""",
    'mensagem de cobrança',
    re.S
)

# 8) Modal de pagamento e prévia: mostra a base correta e total atualizado.
sub_once(
    r"function openPaymentModal\(loanId=''\)\{.*?\n\}\nfunction fillPaymentValue\(\)\{.*?\n\}\nfunction updatePaymentPreview\(\)\{.*?\n\}\nfunction savePayment\(\)\{",
    """function openPaymentModal(loanId=''){
  const openLoans=state.loans.filter(l=>loanTotalDue(l)>0&&!['Cancelado','Renegociado','Excluído'].includes(l.status));
  if(!openLoans.length)return toast('Não há contratos com saldo a receber.');
  const opts=openLoans.map(l=>{
    const c=state.clients.find(x=>x.id===l.clientId);
    return `<option value=\"${l.id}\" ${loanId===l.id?'selected':''}>#${l.contractNo} - ${safe(c?.name||'-')} - saldo ${brl(loanTotalDue(l))}</option>`;
  }).join('');
  modal(`
  <div class=\"modal-header\"><h3>Registrar pagamento</h3><button class=\"btn btn-outline btn-sm\" onclick=\"closeModal()\">Fechar</button></div>
  <div class=\"notice\"><b>Juros por atraso:</b> calculado somente sobre o valor dos juros do contrato. Fórmula: <b>juros ÷ 30 × dias em atraso</b>. O valor principal emprestado não entra nessa base.</div>
  <div class=\"form-grid\">
    <div class=\"field full\"><label>Contrato *</label><select id=\"pLoan\" onchange=\"fillPaymentValue()\">${opts}</select></div>
    <div class=\"field\"><label>Data</label><input id=\"pDate\" type=\"date\" value=\"${todayISO()}\" onchange=\"fillPaymentValue()\"></div>
    <div class=\"field\"><label>Valor recebido *</label><input id=\"pValue\" type=\"number\" min=\"0.01\" step=\"0.01\" oninput=\"updatePaymentPreview()\"></div>
    <div class=\"field\"><label>Forma</label><select id=\"pMethod\"><option>PIX</option><option>Dinheiro</option><option>Transferência</option><option>Cartão</option></select></div>
    <div class=\"field\"><label>Outro encargo manual (opcional)</label><input id=\"pFee\" type=\"number\" min=\"0\" step=\"0.01\" value=\"0\"></div>
    <div class=\"field full\"><label>Observação</label><input id=\"pNotes\"></div>
  </div>
  <div id=\"paymentRulePreview\" class=\"notice\"></div>
  <button id=\"savePaymentBtn\" class=\"btn btn-success\" onclick=\"savePayment()\">Registrar recebimento</button>`);
  fillPaymentValue();
}
function fillPaymentValue(){
  const id=document.getElementById('pLoan')?.value;
  const l=state.loans.find(x=>x.id===id);
  const ref=document.getElementById('pDate')?.value||todayISO();
  if(l)document.getElementById('pValue').value=loanTotalDue(l,ref).toFixed(2);
  updatePaymentPreview();
}
function updatePaymentPreview(){
  const id=document.getElementById('pLoan')?.value;
  const l=state.loans.find(x=>x.id===id);
  const box=document.getElementById('paymentRulePreview');
  if(!l||!box)return;
  const ref=document.getElementById('pDate')?.value||todayISO();
  const baseBal=loanBalance(l),late=loanOverdueInterest(l,ref),bal=baseBal+late;
  const days=loanOverdueDays(l,ref),lateBase=loanInterestBaseForOverdue(l);
  const value=Number(document.getElementById('pValue')?.value||0);
  const cycle=currentCycleNumber(l);
  const lateInfo=days>0?`<div>Base do atraso (somente juros): <b>${brl(lateBase)}</b></div><div>Dias em atraso: <b>${days}</b></div><div>Juros de atraso: <b>${brl(late)}</b> (${brl(lateBase)} ÷ 30 × ${days})</div>`:`<div>Sem juros de atraso até esta data.</div>`;
  if(value<=0){
    box.innerHTML=`<b>Ciclo ${cycle}</b><div style=\"margin-top:8px;display:grid;gap:4px\"><div>Saldo contratual: <b>${brl(baseBal)}</b></div>${lateInfo}<div>Total atualizado: <b>${brl(bal)}</b></div></div>`;
    return;
  }
  if(value>bal+0.009){
    box.innerHTML=`<b style=\"color:var(--danger)\">Valor acima do saldo.</b> O máximo permitido para este contrato é <b>${brl(bal)}</b>.`;
    return;
  }
  const latePaid=Math.min(value,late),contractPaid=Math.max(0,value-latePaid),remaining=Math.max(0,baseBal-contractPaid);
  box.innerHTML=`<b>Ciclo ${cycle}</b><div style=\"margin-top:8px;display:grid;gap:4px\"><div>Saldo contratual: <b>${brl(baseBal)}</b></div>${lateInfo}<div>Total atualizado: <b>${brl(bal)}</b></div><div>Pagamento para juros de atraso: <b>${brl(latePaid)}</b></div><div>Pagamento para contrato: <b>${brl(contractPaid)}</b></div><div>Saldo contratual após pagamento: <b>${brl(remaining)}</b></div></div>`;
}
function savePayment(){""",
    'modal e prévia de pagamento',
    re.S
)

# 9) Salvar pagamento separando encargo de atraso do saldo contratual.
sub_once(
    r"const value=Number\(document\.getElementById\('pValue'\)\?\.value\|\|0\);\s*const bal=loanBalance\(l\);\s*if\(value<=0\)return toast\('Informe o valor recebido\.'\);\s*if\(value>bal\+0\.009\)return toast\(`O pagamento não pode ser maior que o saldo atual \(\$\{brl\(bal\)\}\)\.`\);",
    """const value=Number(document.getElementById('pValue')?.value||0);
  const paymentDate=document.getElementById('pDate')?.value||todayISO();
  const baseBal=loanBalance(l);
  const overdueInterest=loanOverdueInterest(l,paymentDate);
  const bal=baseBal+overdueInterest;
  if(value<=0)return toast('Informe o valor recebido.');
  if(value>bal+0.009)return toast(`O pagamento não pode ser maior que o saldo atual (${brl(bal)}).`);""",
    'saldo total no recebimento',
    re.S
)

sub_once(
    r"const cycleBefore=currentCycleNumber\(l\);\s*const cycle=currentCycleFinancials\(l\);\s*const interestPart=Math\.min\(value,Math\.max\(0,cycle\.interest\)\);\s*const principalPart=Math\.max\(0,Math\.min\(Math\.max\(0,cycle\.base\),value-interestPart\)\);\s*const p=\{\s*id:uid\('pay'\),loanId,date:document\.getElementById\('pDate'\)\.value\|\|todayISO\(\),value,",
    """const cycleBefore=currentCycleNumber(l);
    const cycle=currentCycleFinancials(l);
    const overdueInterestPart=Math.min(value,overdueInterest);
    const contractValue=Math.max(0,value-overdueInterestPart);
    const interestPart=Math.min(contractValue,Math.max(0,cycle.interest));
    const principalPart=Math.max(0,Math.min(Math.max(0,cycle.base),contractValue-interestPart));
    const p={
      id:uid('pay'),loanId,date:paymentDate,value,""",
    'alocação do pagamento',
    re.S
)

s = s.replace(
    "notes:document.getElementById('pNotes').value,principalPart,interestPart,balanceBefore:bal,",
    "notes:document.getElementById('pNotes').value,principalPart,interestPart,overdueInterestPart,overdueDays:loanOverdueDays(l,paymentDate),overdueBase:loanInterestBaseForOverdue(l),balanceBefore:bal,baseBalanceBefore:baseBal,"
)

s = s.replace(
    "if(value<bal-0.009){\n      const remaining=Math.max(0,bal-value);",
    "if(contractValue>0.009 && contractValue<baseBal-0.009){\n      const remaining=Math.max(0,baseBal-contractValue);"
)

s = s.replace(
    "paidTotal:loanPaid(l.id),createdAt:new Date().toISOString(),createdByUserId:getCurrentUser().id||''",
    "paidTotal:loanPaid(l.id),dueDate:plusDays(p.date,30),createdAt:new Date().toISOString(),createdByUserId:getCurrentUser().id||''"
)

# Tratamento da quitação/recebimento apenas de atraso.
s = s.replace(
    "}else{\n      addLoanOccurrence(l,'Pagamento e quitação do contrato',null,null,`Ciclo ${cycleBefore}; saldo antes ${brl(bal)}; pagamento ${brl(value)}; saldo final ${brl(0)}`);\n    }",
    """}else if(contractValue>=baseBal-0.009){
      addLoanOccurrence(l,'Pagamento e quitação do contrato',null,null,`Ciclo ${cycleBefore}; saldo contratual antes ${brl(baseBal)}; juros de atraso ${brl(overdueInterestPart)}; pagamento ${brl(value)}; saldo final ${brl(0)}`);
    }else{
      addLoanOccurrence(l,'Pagamento de juros de atraso',null,null,`Ciclo ${cycleBefore}; juros de atraso recebidos ${brl(overdueInterestPart)}; saldo contratual preservado em ${brl(baseBal)}`);
    }"""
)

# 10) Lista de pagamentos deixa claro o que foi juros de atraso.
s = s.replace(
    "const renewalInfo=p.renewalId?`<div style=\"margin-top:4px;color:var(--primary);font-size:11px;font-weight:700\">Renovação ${p.renewalNo?('#'+p.renewalNo+' · '):''}saldo renovado: ${brl(p.renewedBalance)} (+${brl(p.renewalInterest)} de nova taxa)</div>`:''; return",
    "const overdueInfo=paymentOverduePart(p)>0?`<div style=\"margin-top:4px;color:var(--danger);font-size:11px;font-weight:700\">Juros de atraso recebidos: ${brl(paymentOverduePart(p))}</div>`:''; const renewalInfo=p.renewalId?`<div style=\"margin-top:4px;color:var(--primary);font-size:11px;font-weight:700\">Renovação ${p.renewalNo?('#'+p.renewalNo+' · '):''}saldo renovado: ${brl(p.renewedBalance)} (+${brl(p.renewalInterest)} de nova taxa)</div>`:''; return"
)
s = s.replace("${safe(p.notes||'-')}${renewalInfo}</td></tr>`;", "${safe(p.notes||'-')}${overdueInfo}${renewalInfo}</td></tr>`;")

path.write_text(s, encoding='utf-8')
print('Regra de juros em atraso aplicada com sucesso.')
