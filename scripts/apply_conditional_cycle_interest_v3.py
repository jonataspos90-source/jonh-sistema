from pathlib import Path
import re

index_path = Path('index.html')
sw_path = Path('sw.js')
text = index_path.read_text(encoding='utf-8')

# 1) Regras financeiras centrais: o juro de uma renovacao so vira exigivel depois do novo vencimento.
pattern = re.compile(r"function paymentOverduePart\(p\)\{.*?function loanStatus\(l\)\{", re.S)
replacement = r'''function paymentOverduePart(p){ return Math.max(0,Number(p?.overdueInterestPart||0)); }
function paymentContractPart(p){ return Math.max(0,Number(p?.value||0)-paymentOverduePart(p)); }
function loanPaid(loanId){ return state.payments.filter(p=>p.loanId===loanId).reduce((a,p)=>a+paymentContractPart(p),0); }
function loanOverduePaid(loanId){ return state.payments.filter(p=>p.loanId===loanId).reduce((a,p)=>a+paymentOverduePart(p),0); }
function latestRenewal(l){
  const renewals=Array.isArray(l?.renewals)?l.renewals:[];
  return renewals.length?renewals[renewals.length-1]:null;
}
function currentCycleNumber(l){
  const renewals=Array.isArray(l?.renewals)?l.renewals:[];
  return renewals.length+1;
}
function paymentCycleNumber(p){
  const n=Number(p?.cycleBefore||1);
  return Number.isFinite(n)&&n>0?n:1;
}
function cyclePayments(l,cycleNo){
  return state.payments.filter(p=>p.loanId===l.id && paymentCycleNumber(p)===Number(cycleNo));
}
function loanOriginalInterest(l){
  return Math.max(0,Number(l?.total||0)-Number(l?.principal||0));
}
function loanCurrentDueDate(l){
  const renewal=latestRenewal(l);
  return renewal?.dueDate || l.dueDate || '';
}
function loanOverdueDays(l,referenceDate=todayISO()){
  const due=loanCurrentDueDate(l);
  if(!due||!referenceDate)return 0;
  const d=new Date(due+'T00:00:00');
  const r=new Date(referenceDate+'T00:00:00');
  if(Number.isNaN(d.getTime())||Number.isNaN(r.getTime()))return 0;
  return Math.max(0,Math.floor((r-d)/86400000));
}
function loanInterestBaseForOverdue(l,referenceDate=todayISO()){
  if(!l)return 0;
  const renewal=latestRenewal(l);
  if(renewal)return Math.max(0,Number(renewal.interestAdded||0));
  return loanOriginalInterest(l);
}
function loanCycleOverduePaid(l){
  const cycle=currentCycleNumber(l);
  return cyclePayments(l,cycle).reduce((a,p)=>a+paymentOverduePart(p),0);
}
function currentCycleFinancials(l,referenceDate=todayISO()){
  const renewal=latestRenewal(l);
  if(renewal){
    const cycleNo=Number(renewal.cycleTo||currentCycleNumber(l));
    const pays=[...cyclePayments(l,cycleNo)].sort((a,b)=>String(a.date||'').localeCompare(String(b.date||''))||String(a.id||'').localeCompare(String(b.id||'')));
    const conditionalInterest=Math.max(0,Number(renewal.interestAdded||0));
    let principalPaid=0,interestPaid=0;
    for(const p of pays){
      const hasAllocation=p.principalPart!==undefined || p.interestPart!==undefined;
      if(hasAllocation){
        principalPaid+=Math.max(0,Number(p.principalPart||0));
        interestPaid+=Math.max(0,Number(p.interestPart||0));
        continue;
      }
      const contractValue=paymentContractPart(p);
      if(loanOverdueDays(l,p.date||referenceDate)>0){
        const interestRemaining=Math.max(0,conditionalInterest-interestPaid);
        const ip=Math.min(contractValue,interestRemaining);
        interestPaid+=ip;
        principalPaid+=Math.max(0,contractValue-ip);
      }else{
        principalPaid+=contractValue;
      }
    }
    const principalRemaining=Math.max(0,Number(renewal.baseAfterPayment||0)-principalPaid);
    const interestActive=loanOverdueDays(l,referenceDate)>0 && principalRemaining>0.009;
    const interestRemaining=interestActive?Math.max(0,conditionalInterest-interestPaid):0;
    return {
      base:principalRemaining,
      interest:interestRemaining,
      total:principalRemaining+interestRemaining,
      conditionalInterest,
      interestActive,
      dueDate:renewal.dueDate||''
    };
  }
  const originalInterest=loanOriginalInterest(l);
  const prior=loanPaid(l.id);
  const interestRemaining=Math.max(0,originalInterest-prior);
  const principalPaid=Math.max(0,prior-originalInterest);
  const principalRemaining=Math.max(0,Number(l.principal||0)-principalPaid);
  return {base:principalRemaining,interest:interestRemaining,total:principalRemaining+interestRemaining,conditionalInterest:0,interestActive:true,dueDate:l.dueDate||''};
}
function loanBalance(l,referenceDate=todayISO()){
  if(!l)return 0;
  return Math.max(0,currentCycleFinancials(l,referenceDate).total);
}
function loanOverdueInterest(l,referenceDate=todayISO()){
  if(!l||['Cancelado','Renegociado','Excluído'].includes(l.status)||loanBalance(l,referenceDate)<=0.009)return 0;
  const days=loanOverdueDays(l,referenceDate);
  if(days<=0)return 0;
  const base=loanInterestBaseForOverdue(l,referenceDate);
  const accrued=(base/30)*days;
  return Math.max(0,accrued-loanCycleOverduePaid(l));
}
function loanTotalDue(l,referenceDate=todayISO()){
  return Math.max(0,loanBalance(l,referenceDate)+loanOverdueInterest(l,referenceDate));
}
function loanCurrentInterest(l,referenceDate=todayISO()){
  if(loanBalance(l,referenceDate)<=0.009)return 0;
  return Math.min(loanBalance(l,referenceDate),currentCycleFinancials(l,referenceDate).interest);
}
function loanStatus(l){'''
text, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('Bloco financeiro central nao encontrado')

# 2) Preview de recebimento sempre detalhado.
pattern = re.compile(r"function updatePaymentPreview\(\)\{.*?\n\}\nfunction savePayment\(\)\{", re.S)
replacement = r'''function updatePaymentPreview(){
  const id=document.getElementById('pLoan')?.value;
  const l=state.loans.find(x=>x.id===id);
  const box=document.getElementById('paymentRulePreview');
  if(!l||!box)return;
  const ref=document.getElementById('pDate')?.value||todayISO();
  const cycleNo=currentCycleNumber(l),cycleData=currentCycleFinancials(l,ref),renewal=latestRenewal(l);
  const baseBal=loanBalance(l,ref),late=loanOverdueInterest(l,ref),bal=baseBal+late;
  const days=loanOverdueDays(l,ref),lateBase=loanInterestBaseForOverdue(l,ref);
  const originalInterest=loanOriginalInterest(l);
  const paidTotal=state.payments.filter(p=>p.loanId===l.id).reduce((a,p)=>a+Number(p.value||0),0);
  const value=Number(document.getElementById('pValue')?.value||0);
  const renewalInfo=renewal
    ?(days<=0
      ?`<div>Novo vencimento: <b>${dateBR(renewal.dueDate)}</b></div><div>Juros do próximo ciclo, somente se não quitar até o vencimento: <b>${brl(renewal.interestAdded||0)}</b></div><div>Valor para quitar até o vencimento: <b>${brl(cycleData.base)}</b></div>`
      :`<div>Juros do ciclo vencido: <b>${brl(cycleData.interest)}</b></div>`)
    :`<div>Juros contratuais: <b>${brl(originalInterest)}</b></div>`;
  const lateInfo=days>0
    ?`<div>Base do atraso (juros do ciclo): <b>${brl(lateBase)}</b></div><div>Dias em atraso: <b>${days}</b></div><div>Juros de atraso: <b>${brl(late)}</b> (${brl(lateBase)} ÷ 30 × ${days})</div>`
    :`<div>Sem juros de atraso nesta data.</div>`;
  const detail=`<div style="margin-top:8px;display:grid;gap:4px"><div>Valor original emprestado: <b>${brl(l.principal)}</b></div><div>Juros originais do contrato: <b>${brl(originalInterest)}</b></div><div>Total já recebido: <b>${brl(paidTotal)}</b></div><div>Saldo principal atual: <b>${brl(cycleData.base)}</b></div>${renewalInfo}${lateInfo}<div>Total exigível nesta data: <b>${brl(bal)}</b></div></div>`;
  if(value<=0){ box.innerHTML=`<b>Ciclo ${cycleNo}</b>${detail}`; return; }
  if(value>bal+0.009){
    box.innerHTML=`<b style="color:var(--danger)">Valor acima do saldo.</b> O máximo permitido para este contrato nesta data é <b>${brl(bal)}</b>.${detail}`;
    return;
  }
  const latePaid=Math.min(value,late),contractPaid=Math.max(0,value-latePaid),interestPaid=Math.min(contractPaid,Math.max(0,cycleData.interest)),principalPaid=Math.max(0,contractPaid-interestPaid);
  const principalAfter=Math.max(0,cycleData.base-principalPaid);
  box.innerHTML=`<b>Ciclo ${cycleNo}</b>${detail}<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px;display:grid;gap:4px"><div>Pagamento para atraso: <b>${brl(latePaid)}</b></div><div>Pagamento para juros do ciclo: <b>${brl(interestPaid)}</b></div><div>Pagamento para principal: <b>${brl(principalPaid)}</b></div><div>Principal restante após pagamento: <b>${brl(principalAfter)}</b></div></div>`;
}
function savePayment(){'''
text, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('Funcao updatePaymentPreview nao encontrada')

# 3) Pagamento deve usar a data informada para saber se o juro condicional ja venceu.
text = text.replace("  const baseBal=loanBalance(l);\n  const overdueInterest=loanOverdueInterest(l,paymentDate);", "  const baseBal=loanBalance(l,paymentDate);\n  const overdueInterest=loanOverdueInterest(l,paymentDate);", 1)
text = text.replace("    const cycle=currentCycleFinancials(l);", "    const cycle=currentCycleFinancials(l,paymentDate);", 1)
text = text.replace("overdueBase:loanInterestBaseForOverdue(l),balanceBefore", "overdueBase:loanInterestBaseForOverdue(l,paymentDate),balanceBefore", 1)

# 4) Renovacao: novo juro e apenas previsto; so ativa se ultrapassar o novo vencimento.
pattern = re.compile(r"    let renewedBalance=null;\n    if\(contractValue>0\.009 && contractValue<baseBal-0\.009\)\{.*?    \}else if\(contractValue>=baseBal-0\.009\)\{", re.S)
replacement = r'''    let renewedBalance=null,renewalInterest=0,renewalDueDate='';
    const cycleInterestBefore=Math.max(0,Number(cycle.interest||0));
    const principalRemainingAfter=Math.max(0,Number(cycle.base||0)-principalPart);
    const cycleInterestSettled=cycleInterestBefore>0.009 && interestPart>=cycleInterestBefore-0.009;
    const shouldRenew=principalRemainingAfter>0.009 && cycleInterestSettled;
    if(shouldRenew){
      const remaining=principalRemainingAfter;
      const rate=Math.max(0,Number(l.interest||0));
      const interestAdded=remaining*(rate/100);
      renewalInterest=interestAdded;
      renewedBalance=remaining;
      renewalDueDate=plusDays(p.date,30);
      const renewalNo=(Array.isArray(l.renewals)?l.renewals.length:0)+1;
      const renewal={
        id:uid('ren'),renewalNo,date:p.date,paymentId:p.id,previousBalance:bal,paymentValue:value,
        baseAfterPayment:remaining,interestRate:rate,interestAdded,newBalance:remaining,projectedBalance:remaining+interestAdded,
        interestConditional:true,interestRule:'Cobrar somente se o saldo nao for quitado ate o novo vencimento',
        cycleFrom:cycleBefore,cycleTo:cycleBefore+1,
        paidTotal:loanPaid(l.id),dueDate:renewalDueDate,createdAt:new Date().toISOString(),createdByUserId:getCurrentUser().id||''
      };
      l.renewals=Array.isArray(l.renewals)?l.renewals:[];
      l.renewals.push(renewal);
      p.renewalId=renewal.id;
      p.renewalNo=renewalNo;
      p.renewalInterest=interestAdded;
      p.renewedBalance=remaining;
      p.renewalProjectedBalance=remaining+interestAdded;
      p.renewalDueDate=renewalDueDate;
      p.cycleAfter=cycleBefore+1;
      addLoanOccurrence(l,'Juros do ciclo pagos e saldo renovado',null,null,`Ciclo ${cycleBefore} → ${cycleBefore+1}; pagamento ${brl(value)}; principal restante ${brl(remaining)}; novo vencimento ${dateBR(renewalDueDate)}; juros previstos ${brl(interestAdded)} somente se nao quitar ate o vencimento.`);
    }else if(contractValue>=baseBal-0.009){'''
text, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('Bloco de renovacao nao encontrado')

# Torna o ramo parcial coerente quando houve pagamento de principal/juros sem abrir novo ciclo.
old = """    }else{\n      addLoanOccurrence(l,'Pagamento de juros de atraso',null,null,`Ciclo ${cycleBefore}; juros de atraso recebidos ${brl(overdueInterestPart)}; saldo contratual preservado em ${brl(baseBal)}`);\n    }\n\n    const contractSettled=contractValue>=baseBal-0.009;\n    const paymentResult=renewedBalance!==null\n      ?` → ${cycleBefore+1} - novo saldo ${brl(renewedBalance)}`\n      :(contractSettled?' - quitado':` - juros de atraso recebidos ${brl(overdueInterestPart)}; saldo contratual ${brl(baseBal)}`);\n    audit('Pagamento recebido',`Contrato ${l.contractNo} - ${brl(value)} - ciclo ${cycleBefore}${paymentResult}`);\n    saveState();closeModal();renderAll();\n    if(renewedBalance!==null) toast(`Pagamento parcial registrado. Ciclo ${cycleBefore+1} aberto com saldo de ${brl(renewedBalance)}.`);\n    else if(contractSettled) toast(`Pagamento registrado. Contrato ${l.contractNo} quitado.`);\n    else toast(`Juros de atraso registrados. O saldo contratual permanece em ${brl(baseBal)}.`);"""
new = """    }else if(contractValue>0.009){\n      addLoanOccurrence(l,'Pagamento parcial do ciclo',null,null,`Ciclo ${cycleBefore}; pagamento contratual ${brl(contractValue)}; juros pagos ${brl(interestPart)}; principal pago ${brl(principalPart)}; vencimento mantido em ${dateBR(loanCurrentDueDate(l))}.`);\n    }else{\n      addLoanOccurrence(l,'Pagamento de juros de atraso',null,null,`Ciclo ${cycleBefore}; juros de atraso recebidos ${brl(overdueInterestPart)}; saldo contratual preservado em ${brl(baseBal)}`);\n    }\n\n    const contractSettled=contractValue>=baseBal-0.009;\n    const paymentResult=renewedBalance!==null\n      ?` → ${cycleBefore+1} - principal ${brl(renewedBalance)} - vencimento ${dateBR(renewalDueDate)} - juros condicionais ${brl(renewalInterest)}`\n      :(contractSettled?' - quitado':contractValue>0.009?` - pagamento parcial; principal pago ${brl(principalPart)}; juros pagos ${brl(interestPart)}`:` - juros de atraso recebidos ${brl(overdueInterestPart)}`);\n    audit('Pagamento recebido',`Contrato ${l.contractNo} - ${brl(value)} - ciclo ${cycleBefore}${paymentResult}`);\n    saveState();closeModal();renderAll();\n    if(renewedBalance!==null) toast(`Ciclo ${cycleBefore} encerrado. Principal restante ${brl(renewedBalance)} com novo vencimento em ${dateBR(renewalDueDate)}. Juros de ${brl(renewalInterest)} so serao cobrados se nao quitar ate essa data.`);\n    else if(contractSettled) toast(`Pagamento registrado. Contrato ${l.contractNo} quitado.`);\n    else if(contractValue>0.009) toast(`Pagamento parcial registrado. O vencimento atual foi mantido.`);\n    else toast(`Juros de atraso registrados. O saldo contratual permanece em ${brl(baseBal)}.`);"""
if old not in text:
    raise SystemExit('Bloco de feedback do pagamento nao encontrado')
text = text.replace(old, new, 1)

# 5) Historico de pagamentos deixa claro que o novo juro e condicional.
text = text.replace("saldo renovado: ${brl(p.renewedBalance)} (+${brl(p.renewalInterest)} de nova taxa)", "principal renovado: ${brl(p.renewedBalance)} · vencimento: ${dateBR(p.renewalDueDate||'')} · juros condicionais: ${brl(p.renewalInterest)} (somente se atrasar)", 1)

# 6) Mensagem ao cliente sempre detalha original, juros, pagamentos, saldo, novo vencimento e atraso.
pattern = re.compile(r"function copyCollection\(id\)\{.*?\n\}\nfunction copyLoanMessage\(id\)\{", re.S)
replacement = r'''function copyCollection(id){
  const l=state.loans.find(x=>x.id===id); const c=state.clients.find(x=>x.id===l.clientId);
  if(!l||!c)return toast('Contrato ou cliente não encontrado.');
  const ref=todayISO(),due=loanCurrentDueDate(l),late=loanOverdueInterest(l,ref),days=loanOverdueDays(l,ref);
  const cycle=currentCycleFinancials(l,ref),renewal=latestRenewal(l),originalInterest=loanOriginalInterest(l);
  const paidTotal=state.payments.filter(p=>p.loanId===l.id).reduce((a,p)=>a+Number(p.value||0),0);
  const lines=[
    `Olá, ${c.name}.`,
    '',
    `Segue a posição atualizada do contrato nº ${l.contractNo}:`,
    '',
    `Valor original emprestado: ${brl(l.principal)}`,
    `Juros originais do contrato: ${brl(originalInterest)}`,
    `Total já pago: ${brl(paidTotal)}`,
    `Saldo principal atual: ${brl(cycle.base)}`,
    ...(renewal&&days<=0?[
      `Novo vencimento: ${dateBR(due)}`,
      `Juros do próximo ciclo: ${brl(renewal.interestAdded||0)} (somente se o saldo não for quitado até o vencimento)`,
      `Valor para quitar até o vencimento: ${brl(cycle.base)}`
    ]:[
      `Juros do ciclo atual: ${brl(cycle.interest)}`,
      `Vencimento: ${dateBR(due)}`
    ]),
    ...(late>0?[
      `Dias em atraso: ${days}`,
      `Juros de atraso: ${brl(late)} (${brl(loanInterestBaseForOverdue(l,ref))} ÷ 30 × ${days})`,
      `Total atualizado: ${brl(loanTotalDue(l,ref))}`
    ]:(!renewal?[`Total atual: ${brl(loanTotalDue(l,ref))}`]:[])),
    '',
    'Caso o pagamento já tenha sido realizado, por favor, desconsidere esta mensagem.',
    '',
    'Atenciosamente,',
    'John Sistemas'
  ];
  const msg=lines.join(String.fromCharCode(10));
  navigator.clipboard?.writeText(msg);toast('Mensagem de cobrança detalhada copiada.');
}
function copyLoanMessage(id){'''
text, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('Funcao copyCollection nao encontrada')

# 7) Conta corrente: renovacao nao gera debito imediato. Juros condicionais entram quando vencem; atraso pago/aberto fica visivel.
old = """    state.payments.filter(p=>p.loanId===l.id).forEach(p=>events.push({date:p.date,order:1,desc:`Pagamento contrato #${l.contractNo}`,debit:0,credit:Number(p.value)}));\n    (Array.isArray(l.renewals)?l.renewals:[]).forEach(r=>events.push({date:r.date,order:2,desc:`Renovação do saldo contrato #${l.contractNo} - taxa ${Number(r.interestRate||0).toFixed(2).replace('.',',')}%`,debit:Number(r.interestAdded||0),credit:0}));"""
new = """    state.payments.filter(p=>p.loanId===l.id).forEach(p=>{\n      if(paymentOverduePart(p)>0)events.push({date:p.date,order:0.5,desc:`Juros de atraso do contrato #${l.contractNo}`,debit:paymentOverduePart(p),credit:0});\n      events.push({date:p.date,order:1,desc:`Pagamento contrato #${l.contractNo}`,debit:0,credit:Number(p.value)});\n    });\n    (Array.isArray(l.renewals)?l.renewals:[]).forEach(r=>{\n      events.push({date:r.date,order:2,desc:`Renovação do principal contrato #${l.contractNo} - juros previstos ${brl(r.interestAdded||0)} somente se atrasar até ${dateBR(r.dueDate)}`,debit:0,credit:0});\n      const cycleNo=Number(r.cycleTo||0);\n      const activated=cyclePayments(l,cycleNo).some(p=>Number(p.interestPart||0)>0) || loanOverdueDays({ ...l, renewals:[r] },todayISO())>0;\n      if(activated)events.push({date:r.dueDate,order:2.5,desc:`Juros do ciclo vencido contrato #${l.contractNo}`,debit:Number(r.interestAdded||0),credit:0});\n    });\n    const currentLate=loanOverdueInterest(l);\n    if(currentLate>0)events.push({date:todayISO(),order:3,desc:`Juros de atraso acumulados até hoje contrato #${l.contractNo}`,debit:currentLate,credit:0});"""
if old not in text:
    raise SystemExit('Bloco da conta corrente nao encontrado')
text = text.replace(old, new, 1)

# 8) Texto da regra no modal.
text = text.replace(
    '<div class="notice"><b>Juros por atraso:</b> calculado somente sobre o valor dos juros do contrato. Fórmula: <b>juros ÷ 30 × dias em atraso</b>. O valor principal emprestado não entra nessa base.</div>',
    '<div class="notice"><b>Regra por ciclo:</b> após pagar os juros do ciclo e restar principal, o saldo recebe um novo vencimento. O próximo juro fica apenas previsto e só é cobrado se esse novo vencimento for ultrapassado. Depois do vencimento, o atraso é <b>juros do ciclo ÷ 30 × dias em atraso</b>.</div>',
    1
)

# 9) PWA/iOS: força a nova regra no app instalado.
text = text.replace("./sw.js?v=99", "./sw.js?v=100", 1)
index_path.write_text(text, encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(r"const CACHE_NAME='john-sistemas-pwa-[^']+';", "const CACHE_NAME='john-sistemas-pwa-v100-conditional-cycle-interest';", sw, count=1)
sw_path.write_text(sw, encoding='utf-8')

# Validacoes estaticas basicas.
checks = [
    'interestConditional:true',
    'projectedBalance:remaining+interestAdded',
    'Juros do próximo ciclo',
    "./sw.js?v=100",
    "john-sistemas-pwa-v100-conditional-cycle-interest"
]
for item in checks:
    hay = text if item != 'john-sistemas-pwa-v100-conditional-cycle-interest' else sw
    if item not in hay:
        raise SystemExit(f'Validacao ausente: {item}')

print('Patch de juros condicionais por ciclo aplicado com sucesso.')
