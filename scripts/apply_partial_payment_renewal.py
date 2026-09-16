from pathlib import Path
import re

path = Path('index.html')
s = path.read_text(encoding='utf-8')

s = s.replace('<title>Jonh Sistema - Gestão de Empréstimos V9</title>', '<title>Jonh Sistema - Gestão de Empréstimos V9.1</title>')
s = s.replace("const APP_VERSION = '9.0';", "const APP_VERSION = '9.1';")

old = "out.loans=Array.isArray(out.loans)?out.loans.map(l=>({...l,occurrences:Array.isArray(l.occurrences)?l.occurrences:[]})):[];"
new = "out.loans=Array.isArray(out.loans)?out.loans.map(l=>({...l,occurrences:Array.isArray(l.occurrences)?l.occurrences:[],renewals:Array.isArray(l.renewals)?l.renewals:[]})):[];"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('Falha: normalização de empréstimos não encontrada')

pattern = r"function loanPaid\(loanId\)\{.*?\n\nfunction renderDashboard\(\)\{"
replacement = '''function loanPaid(loanId){ return state.payments.filter(p=>p.loanId===loanId).reduce((a,b)=>a+Number(b.value),0); }
function latestRenewal(l){
  const renewals=Array.isArray(l?.renewals)?l.renewals:[];
  return renewals.length?renewals[renewals.length-1]:null;
}
function loanBalance(l){
  const renewal=latestRenewal(l);
  if(renewal){
    const paidAfter=Math.max(0,loanPaid(l.id)-Number(renewal.paidTotal||0));
    return Math.max(0,Number(renewal.newBalance||0)-paidAfter);
  }
  return Math.max(0,Number(l.total)-loanPaid(l.id));
}
function currentCycleFinancials(l){
  const renewal=latestRenewal(l);
  if(renewal){
    const paidAfter=Math.max(0,loanPaid(l.id)-Number(renewal.paidTotal||0));
    const interestRemaining=Math.max(0,Number(renewal.interestAdded||0)-paidAfter);
    const principalPaid=Math.max(0,paidAfter-Number(renewal.interestAdded||0));
    const principalRemaining=Math.max(0,Number(renewal.baseAfterPayment||0)-principalPaid);
    return {base:principalRemaining,interest:interestRemaining,total:principalRemaining+interestRemaining};
  }
  const originalInterest=Math.max(0,Number(l.total||0)-Number(l.principal||0));
  const prior=loanPaid(l.id);
  const interestRemaining=Math.max(0,originalInterest-prior);
  const principalPaid=Math.max(0,prior-originalInterest);
  const principalRemaining=Math.max(0,Number(l.principal||0)-principalPaid);
  return {base:principalRemaining,interest:interestRemaining,total:principalRemaining+interestRemaining};
}
function loanCurrentInterest(l){
  if(loanBalance(l)<=0.009)return 0;
  return Math.min(loanBalance(l),currentCycleFinancials(l).interest);
}
function loanStatus(l){
  if(['Cancelado','Renegociado','Excluído'].includes(l.status))return l.status;
  const bal=loanBalance(l);
  if(bal<=0.009)return 'Quitado';
  if(new Date(l.dueDate+'T23:59:59')<new Date())return 'Vencido';
  if(loanPaid(l.id)>0)return 'Parcial';
  return 'Em aberto';
}
function badgeStatus(s){
  const c=s==='Quitado'?'success':s==='Vencido'?'danger':s==='Parcial'?'warn':s==='Excluído'?'danger':'info';
  return `<span class="badge ${c}">${safe(s)}</span>`;
}
function currentMonthPayments(){
  const m=document.getElementById('dreMonth')?.value||monthISO();
  return state.payments.filter(p=>p.date.startsWith(m));
}
function paymentAllocation(p){
  if(p && (p.principalPart!==undefined || p.interestPart!==undefined)){
    return {principal:Number(p.principalPart||0),interest:Number(p.interestPart||0)};
  }
  const loan=state.loans.find(l=>l.id===p.loanId);
  if(!loan)return {principal:0,interest:Number(p.value)};
  const prior=state.payments.filter(x=>x.loanId===p.loanId && (x.date<p.date || (x.date===p.date && x.id<p.id))).reduce((a,b)=>a+Number(b.value),0);
  const originalInterest=Math.max(0,Number(loan.total||0)-Number(loan.principal||0));
  const interestRemaining=Math.max(0,originalInterest-prior);
  const interestPart=Math.min(Number(p.value||0),interestRemaining);
  const principalPart=Math.max(0,Math.min(Number(loan.principal||0),Number(p.value||0)-interestPart));
  return {principal:principalPart,interest:interestPart};
}

function renderDashboard(){'''
if 'function latestRenewal(l)' not in s:
    s, n = re.subn(pattern, lambda m: replacement, s, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'Falha: bloco financeiro encontrado {n} vez(es)')

old_interest = "const interestPrev=state.loans.filter(l=>l.status!=='Cancelado' && l.status!=='Excluído').reduce((a,l)=>a+(Number(l.total)-Number(l.principal)),0);"
new_interest = "const interestPrev=state.loans.filter(l=>l.status!=='Cancelado' && l.status!=='Excluído').reduce((a,l)=>a+loanCurrentInterest(l),0);"
if old_interest in s:
    s = s.replace(old_interest, new_interest, 1)
elif new_interest not in s:
    raise SystemExit('Falha: KPI de juros previstos não encontrado')

pattern = r"function openPaymentModal\(loanId=''\)\{.*?\nfunction renderPayments\(\)\{"
replacement = '''function openPaymentModal(loanId=''){
  const openLoans=state.loans.filter(l=>loanBalance(l)>0&&!['Cancelado','Renegociado','Excluído'].includes(l.status));
  if(!openLoans.length)return toast('Não há contratos com saldo a receber.');
  const opts=openLoans.map(l=>{
    const c=state.clients.find(x=>x.id===l.clientId);
    return `<option value="${l.id}" ${loanId===l.id?'selected':''}>#${l.contractNo} - ${safe(c?.name||'-')} - saldo ${brl(loanBalance(l))}</option>`;
  }).join('');
  modal(`
  <div class="modal-header"><h3>Registrar pagamento</h3><button class="btn btn-outline btn-sm" onclick="closeModal()">Fechar</button></div>
  <div class="notice"><b>Regra de pagamento parcial:</b> o valor que restar em aberto recebe novamente a mesma taxa percentual do contrato. Ex.: saldo R$ 140,00, pagamento R$ 40,00, sobra R$ 100,00; com taxa de 40%, o novo saldo volta para R$ 140,00.</div>
  <div class="form-grid">
    <div class="field full"><label>Contrato *</label><select id="pLoan" onchange="fillPaymentValue()">${opts}</select></div>
    <div class="field"><label>Data</label><input id="pDate" type="date" value="${todayISO()}"></div>
    <div class="field"><label>Valor recebido *</label><input id="pValue" type="number" min="0.01" step="0.01" oninput="updatePaymentPreview()"></div>
    <div class="field"><label>Forma</label><select id="pMethod"><option>PIX</option><option>Dinheiro</option><option>Transferência</option><option>Cartão</option></select></div>
    <div class="field"><label>Multa/encargo dentro do valor</label><input id="pFee" type="number" min="0" step="0.01" value="0"></div>
    <div class="field full"><label>Observação</label><input id="pNotes"></div>
  </div>
  <div id="paymentRulePreview" class="notice"></div>
  <button class="btn btn-success" onclick="savePayment()">Registrar recebimento</button>`);
  fillPaymentValue();
}
function fillPaymentValue(){
  const id=document.getElementById('pLoan')?.value; const l=state.loans.find(x=>x.id===id);
  if(l)document.getElementById('pValue').value=loanBalance(l).toFixed(2);
  updatePaymentPreview();
}
function updatePaymentPreview(){
  const id=document.getElementById('pLoan')?.value;
  const l=state.loans.find(x=>x.id===id);
  const box=document.getElementById('paymentRulePreview');
  if(!l||!box)return;
  const bal=loanBalance(l);
  const value=Number(document.getElementById('pValue')?.value||0);
  if(value<=0){
    box.innerHTML=`Saldo atual: <b>${brl(bal)}</b>. Informe o valor recebido para visualizar o cálculo.`;
    return;
  }
  if(value>=bal-0.009){
    box.innerHTML=`Pagamento de <b>${brl(value)}</b> quita o saldo atual de <b>${brl(bal)}</b>. Não haverá renovação de juros.`;
    return;
  }
  const remaining=Math.max(0,bal-value);
  const rate=Math.max(0,Number(l.interest||0));
  const newInterest=remaining*(rate/100);
  const newBalance=remaining+newInterest;
  box.innerHTML=`Pagamento parcial: saldo atual <b>${brl(bal)}</b> − pagamento <b>${brl(value)}</b> = base renovada <b>${brl(remaining)}</b>. Nova taxa de <b>${rate.toFixed(2).replace('.',',')}%</b>: <b>${brl(newInterest)}</b>. Novo saldo a pagar: <b>${brl(newBalance)}</b>.`;
}
function savePayment(){
  const loanId=document.getElementById('pLoan').value; const l=state.loans.find(x=>x.id===loanId);
  if(!l)return toast('Contrato não encontrado.');
  const value=Number(document.getElementById('pValue').value||0); const bal=loanBalance(l);
  if(value<=0)return toast('Informe o valor recebido.');
  if(value>bal+0.001 && !confirm(`O valor informado é maior que o saldo do contrato (${brl(bal)}). Continuar mesmo assim?`))return;

  const cycle=currentCycleFinancials(l);
  const interestPart=Math.min(value,Math.max(0,cycle.interest));
  const principalPart=Math.max(0,Math.min(Math.max(0,cycle.base),value-interestPart));
  const p={
    id:uid('pay'),loanId,date:document.getElementById('pDate').value||todayISO(),value,
    method:document.getElementById('pMethod').value,fee:Number(document.getElementById('pFee').value||0),
    notes:document.getElementById('pNotes').value,principalPart,interestPart,balanceBefore:bal
  };
  state.payments.push(p);

  let renewedBalance=null;
  if(value<bal-0.009){
    const remaining=Math.max(0,bal-value);
    const rate=Math.max(0,Number(l.interest||0));
    const interestAdded=remaining*(rate/100);
    renewedBalance=remaining+interestAdded;
    const renewal={
      id:uid('ren'),date:p.date,paymentId:p.id,previousBalance:bal,paymentValue:value,
      baseAfterPayment:remaining,interestRate:rate,interestAdded,newBalance:renewedBalance,
      paidTotal:loanPaid(l.id),createdAt:new Date().toISOString(),createdByUserId:getCurrentUser().id||''
    };
    l.renewals=Array.isArray(l.renewals)?l.renewals:[];
    l.renewals.push(renewal);
    p.renewalId=renewal.id;
    p.renewalInterest=interestAdded;
    p.renewedBalance=renewedBalance;
    addLoanOccurrence(l,'Saldo renovado após pagamento parcial',null,null,`Saldo antes ${brl(bal)}; pagamento ${brl(value)}; base renovada ${brl(remaining)}; taxa ${rate.toFixed(2)}%; novo saldo ${brl(renewedBalance)}`);
  }

  audit('Pagamento recebido',`Contrato ${l.contractNo} - ${brl(value)}${renewedBalance!==null?' - novo saldo '+brl(renewedBalance):''}`);
  saveState();closeModal();renderAll();
  if(renewedBalance!==null) toast(`Pagamento parcial registrado. Novo saldo do contrato ${l.contractNo}: ${brl(renewedBalance)}.`);
  else toast(loanBalance(l)<=0.009?`Pagamento registrado. Contrato ${l.contractNo} quitado.`:'Pagamento registrado com sucesso.');
}
function renderPayments(){'''
if 'function updatePaymentPreview()' not in s:
    s, n = re.subn(pattern, lambda m: replacement, s, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'Falha: fluxo de pagamento encontrado {n} vez(es)')

old_row = "return `<tr><td>${dateBR(p.date)}</td><td>${safe(c?.name||'-')}</td><td>#${l?.contractNo||'-'}</td><td>${brl(p.value)}</td><td>${brl(al.principal)}</td><td>${brl(al.interest+Number(p.fee||0))}</td><td>${safe(p.method)}</td><td>${safe(p.notes||'-')}</td></tr>`;"
new_row = "const renewalInfo=p.renewalId?`<div style=\"margin-top:4px;color:var(--primary);font-size:11px;font-weight:700\">Saldo renovado: ${brl(p.renewedBalance)} (+${brl(p.renewalInterest)} de nova taxa)</div>`:''; return `<tr><td>${dateBR(p.date)}</td><td>${safe(c?.name||'-')}</td><td>#${l?.contractNo||'-'}</td><td>${brl(p.value)}</td><td>${brl(al.principal)}</td><td>${brl(al.interest+Number(p.fee||0))}</td><td>${safe(p.method)}</td><td>${safe(p.notes||'-')}${renewalInfo}</td></tr>`;"
if old_row in s:
    s = s.replace(old_row, new_row, 1)
elif 'Saldo renovado:' not in s:
    raise SystemExit('Falha: linha de recebimentos não encontrada')

old_account = """    events.push({date:l.date,order:0,desc:`Contrato #${l.contractNo} - valor total contratado`,debit:Number(l.total),credit:0});
    state.payments.filter(p=>p.loanId===l.id).forEach(p=>events.push({date:p.date,order:1,desc:`Pagamento contrato #${l.contractNo}`,debit:0,credit:Number(p.value)}));
  });"""
new_account = """    events.push({date:l.date,order:0,desc:`Contrato #${l.contractNo} - valor total contratado`,debit:Number(l.total),credit:0});
    state.payments.filter(p=>p.loanId===l.id).forEach(p=>events.push({date:p.date,order:1,desc:`Pagamento contrato #${l.contractNo}`,debit:0,credit:Number(p.value)}));
    (Array.isArray(l.renewals)?l.renewals:[]).forEach(r=>events.push({date:r.date,order:2,desc:`Renovação do saldo contrato #${l.contractNo} - taxa ${Number(r.interestRate||0).toFixed(2).replace('.',',')}%`,debit:Number(r.interestAdded||0),credit:0}));
  });"""
if old_account in s:
    s = s.replace(old_account, new_account, 1)
elif 'Renovação do saldo contrato' not in s:
    raise SystemExit('Falha: conta corrente não encontrada')

path.write_text(s, encoding='utf-8')
print('Melhoria de pagamento parcial aplicada com sucesso.')
