from pathlib import Path

INDEX = Path('index.html')
SW = Path('sw.js')
text = INDEX.read_text(encoding='utf-8')


def replace_between(source: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = source.find(start_marker)
    if start < 0:
        raise SystemExit(f'Marcador inicial não encontrado: {start_marker}')
    end = source.find(end_marker, start)
    if end < 0:
        raise SystemExit(f'Marcador final não encontrado: {end_marker}')
    return source[:start] + replacement.rstrip() + '\n' + source[end:]


financial_helpers = r'''function paymentOverduePart(p){ return Math.max(0,Number(p?.overdueInterestPart||0)); }
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
function paymentCycleNo(p){ return Math.max(1,Number(p?.cycleBefore||1)); }
function cyclePayments(l,cycleNo,untilDate=''){
  return state.payments
    .filter(p=>p.loanId===l.id && paymentCycleNo(p)===Number(cycleNo) && (!untilDate || !p.date || p.date<=untilDate))
    .sort((a,b)=>String(a.date||'').localeCompare(String(b.date||''))||String(a.id||'').localeCompare(String(b.id||'')));
}
function cycleAllocationTotals(l,cycleNo,interestDue=0,untilDate=''){
  let interest=0,principal=0;
  cyclePayments(l,cycleNo,untilDate).forEach(p=>{
    if(p.interestPart!==undefined || p.principalPart!==undefined){
      interest+=Math.max(0,Number(p.interestPart||0));
      principal+=Math.max(0,Number(p.principalPart||0));
      return;
    }
    const contractValue=paymentContractPart(p);
    const interestPart=Math.min(contractValue,Math.max(0,Number(interestDue||0)-interest));
    interest+=interestPart;
    principal+=Math.max(0,contractValue-interestPart);
  });
  return {interest,principal,total:interest+principal};
}
function loanOverduePaidForCycle(l,cycleNo,untilDate=''){
  return state.payments
    .filter(p=>p.loanId===l.id && paymentCycleNo(p)===Number(cycleNo) && (!untilDate || !p.date || p.date<=untilDate))
    .reduce((a,p)=>a+paymentOverduePart(p),0);
}
function renewalCycleNo(r){ return Math.max(2,Number(r?.cycleTo||((r?.renewalNo||1)+1))); }
function renewalPrincipalAtDue(l,r){
  if(!r)return 0;
  const base=Math.max(0,Number(r.baseAfterPayment||0));
  const paidByDue=cycleAllocationTotals(l,renewalCycleNo(r),0,r.dueDate||'').principal;
  return Math.max(0,base-paidByDue);
}
function renewalConditionalInterestAmount(l,r){
  if(!r)return 0;
  const rate=Math.max(0,Number(r.interestRate??l?.interest??0));
  return renewalPrincipalAtDue(l,r)*(rate/100);
}
function renewalInterestActive(r,referenceDate=todayISO()){
  return Boolean(r?.dueDate && referenceDate && referenceDate>r.dueDate);
}
function loanCurrentDueDate(l){
  const renewal=latestRenewal(l);
  return renewal?.dueDate || l.dueDate || '';
}
function currentCycleFinancials(l,referenceDate=todayISO()){
  const renewal=latestRenewal(l);
  if(renewal){
    const cycleNo=renewalCycleNo(renewal);
    const rate=Math.max(0,Number(renewal.interestRate??l.interest??0));
    const interestActive=renewalInterestActive(renewal,referenceDate);
    const activatedInterest=renewalConditionalInterestAmount(l,renewal);
    const interestDue=interestActive?activatedInterest:0;
    const paid=cycleAllocationTotals(l,cycleNo,interestDue,referenceDate);
    const principalRemaining=Math.max(0,Number(renewal.baseAfterPayment||0)-paid.principal);
    const interestRemaining=Math.max(0,interestDue-paid.interest);
    const conditionalPreview=interestActive?0:principalRemaining*(rate/100);
    return {base:principalRemaining,interest:interestRemaining,total:principalRemaining+interestRemaining,cycleNo,dueDate:renewal.dueDate||'',interestActive,activatedInterest,conditionalInterest:conditionalPreview};
  }
  const originalInterest=Math.max(0,Number(l.total||0)-Number(l.principal||0));
  const paid=cycleAllocationTotals(l,1,originalInterest,referenceDate);
  const interestRemaining=Math.max(0,originalInterest-paid.interest);
  const principalRemaining=Math.max(0,Number(l.principal||0)-paid.principal);
  return {base:principalRemaining,interest:interestRemaining,total:principalRemaining+interestRemaining,cycleNo:1,dueDate:l.dueDate||'',interestActive:true,activatedInterest:originalInterest,conditionalInterest:0};
}
function loanBalance(l,referenceDate=todayISO()){
  return Math.max(0,currentCycleFinancials(l,referenceDate).total);
}
function loanInterestBaseForOverdue(l,referenceDate=todayISO()){
  if(!l)return 0;
  const renewal=latestRenewal(l);
  if(renewal)return Math.max(0,renewalConditionalInterestAmount(l,renewal));
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
  if(!l||['Cancelado','Renegociado','Excluído'].includes(l.status)||loanBalance(l,referenceDate)<=0.009)return 0;
  const days=loanOverdueDays(l,referenceDate);
  if(days<=0)return 0;
  const base=loanInterestBaseForOverdue(l,referenceDate);
  const accrued=(base/30)*days;
  const paid=loanOverduePaidForCycle(l,currentCycleNumber(l),referenceDate);
  return Math.max(0,accrued-paid);
}
function loanTotalDue(l,referenceDate=todayISO()){
  return Math.max(0,loanBalance(l,referenceDate)+loanOverdueInterest(l,referenceDate));
}
function loanConditionalInterestPreview(l,referenceDate=todayISO()){
  return Math.max(0,Number(currentCycleFinancials(l,referenceDate).conditionalInterest||0));
}
function loanCurrentInterest(l,referenceDate=todayISO()){
  if(loanBalance(l,referenceDate)<=0.009)return 0;
  return Math.max(0,currentCycleFinancials(l,referenceDate).interest);
}
function loanFinancialBreakdown(l,referenceDate=todayISO()){
  const cycle=currentCycleFinancials(l,referenceDate);
  const originalPrincipal=Math.max(0,Number(l?.principal||0));
  const rate=Math.max(0,Number(l?.interest||0));
  const originalInterest=originalPrincipal*(rate/100);
  const overdueDays=loanOverdueDays(l,referenceDate);
  const overdueInterest=loanOverdueInterest(l,referenceDate);
  return {originalPrincipal,rate,originalInterest,principalRemaining:cycle.base,currentInterest:cycle.interest,conditionalInterest:cycle.conditionalInterest||0,interestActive:Boolean(cycle.interestActive),overdueDays,overdueInterest,dueDate:loanCurrentDueDate(l),total:loanTotalDue(l,referenceDate),cycleNo:cycle.cycleNo||currentCycleNumber(l)};
}
function loanStatus(l){
  if(['Cancelado','Renegociado','Excluído'].includes(l.status))return l.status;
  const bal=loanTotalDue(l);
  if(bal<=0.009)return 'Quitado';
  if(new Date(loanCurrentDueDate(l)+'T23:59:59')<new Date())return 'Vencido';
  if(loanPaid(l.id)>0)return 'Parcial';
  return 'Em aberto';
}
'''
text = replace_between(text, 'function paymentOverduePart', 'function badgeStatus', financial_helpers)

preview = r'''function updatePaymentPreview(){
  const id=document.getElementById('pLoan')?.value;
  const l=state.loans.find(x=>x.id===id);
  const box=document.getElementById('paymentRulePreview');
  if(!l||!box)return;
  const ref=document.getElementById('pDate')?.value||todayISO();
  const cycle=currentCycleFinancials(l,ref);
  const details=loanFinancialBreakdown(l,ref);
  const late=details.overdueInterest,bal=details.total;
  const value=Number(document.getElementById('pValue')?.value||0);
  const renewal=latestRenewal(l);
  const lateBase=loanInterestBaseForOverdue(l,ref);
  const conditionalInfo=renewal&&!cycle.interestActive&&cycle.base>0.009?`<div style="margin-top:6px;padding:8px 10px;border-radius:9px;background:#fff8e6"><b>Próximo juros previsto:</b> ${brl(details.conditionalInterest)}. <b>Não está sendo cobrado agora.</b> Só será devido se o saldo principal não for quitado até ${dateBR(details.dueDate)}.</div>`:'';
  const lateInfo=details.overdueDays>0?`<div>Juros do ciclo vencido (base do atraso): <b>${brl(lateBase)}</b></div><div>Dias em atraso: <b>${details.overdueDays}</b></div><div>Acréscimo por atraso: <b>${brl(late)}</b> (${brl(lateBase)} ÷ 30 × ${details.overdueDays})</div>`:`<div>Sem acréscimo por atraso até esta data.</div>`;
  const summary=`<b>Ciclo ${details.cycleNo}</b><div style="margin-top:8px;display:grid;gap:4px"><div>Valor original do contrato: <b>${brl(details.originalPrincipal)}</b></div><div>Juros contratados no 1º ciclo (${details.rate.toFixed(2).replace('.',',')}%): <b>${brl(details.originalInterest)}</b></div><div>Saldo principal atual: <b>${brl(details.principalRemaining)}</b></div><div>Juros atualmente em aberto: <b>${brl(details.currentInterest)}</b></div>${conditionalInfo}${lateInfo}<div>Total para quitação nesta data: <b>${brl(bal)}</b></div></div>`;
  if(value<=0){ box.innerHTML=summary; return; }
  if(value>bal+0.009){ box.innerHTML=`${summary}<div style="margin-top:8px"><b style="color:var(--danger)">Valor acima do saldo.</b> O máximo permitido é <b>${brl(bal)}</b>.</div>`; return; }
  const latePaid=Math.min(value,late);
  const contractPaid=Math.max(0,value-latePaid);
  const interestPaid=Math.min(contractPaid,Math.max(0,cycle.interest));
  const principalPaid=Math.max(0,Math.min(Math.max(0,cycle.base),contractPaid-interestPaid));
  const remainingInterest=Math.max(0,cycle.interest-interestPaid);
  const remainingPrincipal=Math.max(0,cycle.base-principalPaid);
  let renewalInfo='';
  if(cycle.interest>0.009 && remainingInterest<=0.009 && remainingPrincipal>0.009){
    const newDue=plusDays(ref,30); const futureInterest=remainingPrincipal*(details.rate/100);
    renewalInfo=`<div style="margin-top:7px;padding:9px 10px;border-radius:9px;background:#e9f8f0;color:#08753e"><b>Novo ciclo:</b> restarão ${brl(remainingPrincipal)} de principal, com novo vencimento em <b>${dateBR(newDue)}</b>. O próximo juros previsto será de <b>${brl(futureInterest)}</b>, mas só será cobrado se esse principal não for quitado até o novo vencimento.</div>`;
  }
  box.innerHTML=`${summary}<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:8px;display:grid;gap:4px"><div>Pagamento para atraso: <b>${brl(latePaid)}</b></div><div>Pagamento para juros do ciclo: <b>${brl(interestPaid)}</b></div><div>Pagamento para principal: <b>${brl(principalPaid)}</b></div><div>Principal restante após pagamento: <b>${brl(remainingPrincipal)}</b></div><div>Juros atuais restantes após pagamento: <b>${brl(remainingInterest)}</b></div>${renewalInfo}</div>`;
}
'''
text = replace_between(text, 'function updatePaymentPreview', 'function savePayment', preview)

save_payment = r'''function savePayment(){
  const loanId=document.getElementById('pLoan')?.value;
  const l=state.loans.find(x=>x.id===loanId);
  if(!l)return toast('Contrato não encontrado.');
  const value=Number(document.getElementById('pValue')?.value||0);
  const paymentDate=document.getElementById('pDate')?.value||todayISO();
  const cycle=currentCycleFinancials(l,paymentDate);
  const baseBal=loanBalance(l,paymentDate);
  const overdueInterest=loanOverdueInterest(l,paymentDate);
  const bal=baseBal+overdueInterest;
  if(value<=0)return toast('Informe o valor recebido.');
  if(value>bal+0.009)return toast(`O pagamento não pode ser maior que o saldo atual (${brl(bal)}).`);
  const btn=document.getElementById('savePaymentBtn'); if(btn?.disabled)return; if(btn)btn.disabled=true;
  try{
    const cycleBefore=currentCycleNumber(l);
    const overdueInterestPart=Math.min(value,overdueInterest);
    const contractValue=Math.max(0,value-overdueInterestPart);
    const interestPart=Math.min(contractValue,Math.max(0,cycle.interest));
    const principalPart=Math.max(0,Math.min(Math.max(0,cycle.base),contractValue-interestPart));
    const remainingInterest=Math.max(0,cycle.interest-interestPart);
    const remainingPrincipal=Math.max(0,cycle.base-principalPart);
    const remainingOverdue=Math.max(0,overdueInterest-overdueInterestPart);
    const p={id:uid('pay'),loanId,date:paymentDate,value,method:document.getElementById('pMethod').value,fee:Number(document.getElementById('pFee').value||0),notes:document.getElementById('pNotes').value,principalPart,interestPart,overdueInterestPart,overdueDays:loanOverdueDays(l,paymentDate),overdueBase:loanInterestBaseForOverdue(l,paymentDate),balanceBefore:bal,baseBalanceBefore:baseBal,cycleBefore,cycleAfter:cycleBefore};
    state.payments.push(p);
    let renewal=null;
    const interestCycleSettled=cycle.interest>0.009 && remainingInterest<=0.009 && remainingPrincipal>0.009;
    if(interestCycleSettled){
      const rate=Math.max(0,Number(l.interest||0));
      const dueDate=plusDays(p.date,30);
      const futureInterest=remainingPrincipal*(rate/100);
      const renewalNo=(Array.isArray(l.renewals)?l.renewals.length:0)+1;
      renewal={id:uid('ren'),renewalNo,date:p.date,paymentId:p.id,previousBalance:bal,paymentValue:value,baseAfterPayment:remainingPrincipal,interestRate:rate,interestAdded:futureInterest,conditionalInterest:futureInterest,interestConditional:true,activationRule:'after_due',newBalance:remainingPrincipal,projectedBalanceIfOverdue:remainingPrincipal+futureInterest,cycleFrom:cycleBefore,cycleTo:cycleBefore+1,paidTotal:loanPaid(l.id),dueDate,createdAt:new Date().toISOString(),createdByUserId:getCurrentUser().id||''};
      l.renewals=Array.isArray(l.renewals)?l.renewals:[]; l.renewals.push(renewal);
      p.renewalId=renewal.id; p.renewalNo=renewalNo; p.renewalInterest=futureInterest; p.renewedBalance=remainingPrincipal; p.renewalDueDate=dueDate; p.cycleAfter=cycleBefore+1;
      addLoanOccurrence(l,'Juros do ciclo recebidos e saldo renovado',null,null,`Ciclo ${cycleBefore} → ${cycleBefore+1}; pagamento ${brl(value)}; principal restante ${brl(remainingPrincipal)}; novo vencimento ${dateBR(dueDate)}; próximo juros previsto ${brl(futureInterest)} - somente será cobrado se o principal não for quitado até o novo vencimento.`);
    }
    const contractSettled=!renewal && remainingPrincipal<=0.009 && remainingInterest<=0.009 && remainingOverdue<=0.009;
    if(contractSettled)addLoanOccurrence(l,'Pagamento e quitação do contrato',null,null,`Ciclo ${cycleBefore}; pagamento ${brl(value)}; principal ${brl(principalPart)}; juros ${brl(interestPart)}; atraso ${brl(overdueInterestPart)}; saldo final ${brl(0)}`);
    else if(!renewal)addLoanOccurrence(l,'Pagamento parcial',null,null,`Ciclo ${cycleBefore}; pagamento ${brl(value)}; atraso ${brl(overdueInterestPart)}; juros ${brl(interestPart)}; principal ${brl(principalPart)}; saldo atualizado ${brl(loanTotalDue(l,paymentDate))}`);
    const currentAfter=loanTotalDue(l,paymentDate);
    audit('Pagamento recebido',`Contrato ${l.contractNo} - ${brl(value)} - ciclo ${cycleBefore}${renewal?` → ${cycleBefore+1}; principal ${brl(remainingPrincipal)}; vencimento ${dateBR(renewal.dueDate)}; juros futuros ${brl(renewal.conditionalInterest)} condicionais ao atraso`:(contractSettled?' - quitado':` - saldo atualizado ${brl(currentAfter)}`)}`);
    saveState();closeModal();renderAll();
    if(renewal) toast(`Pagamento registrado. Principal restante ${brl(remainingPrincipal)} com novo vencimento em ${dateBR(renewal.dueDate)}. Próximo juros só será cobrado se houver atraso.`);
    else if(contractSettled) toast(`Pagamento registrado. Contrato ${l.contractNo} quitado.`);
    else toast(`Pagamento parcial registrado. Saldo atualizado: ${brl(currentAfter)}.`);
  }catch(err){ console.error(err); if(btn)btn.disabled=false; toast('Não foi possível registrar o pagamento. Revise os dados antes de tentar novamente.'); }
}
'''
text = replace_between(text, 'function savePayment', 'function renderPayments', save_payment)

render_payments = r'''function renderPayments(){
  document.getElementById('paymentsTable').innerHTML=state.payments.length?[...state.payments].sort((a,b)=>b.date.localeCompare(a.date)).map(p=>{
    const l=state.loans.find(x=>x.id===p.loanId); const c=state.clients.find(x=>x.id===l?.clientId); const al=paymentAllocation(p);
    const overdueInfo=paymentOverduePart(p)>0?`<div style="margin-top:4px;color:var(--danger);font-size:11px;font-weight:700">Acréscimo por atraso recebido: ${brl(paymentOverduePart(p))}</div>`:'';
    const renewalInfo=p.renewalId?`<div style="margin-top:4px;color:var(--primary);font-size:11px;font-weight:700">Novo ciclo ${p.renewalNo?('#'+p.renewalNo+' · '):''}principal: ${brl(p.renewedBalance)} · vencimento: ${dateBR(p.renewalDueDate||'')} · juros previstos: ${brl(p.renewalInterest)} (somente se não quitar até o vencimento)</div>`:'';
    return `<tr><td>${dateBR(p.date)}</td><td>${safe(c?.name||'-')}</td><td>#${l?.contractNo||'-'}</td><td>${brl(p.value)}</td><td>${brl(al.principal)}</td><td>${brl(al.interest+Number(p.fee||0))}</td><td>${safe(p.method)}</td><td>${safe(p.notes||'-')}${overdueInfo}${renewalInfo}</td></tr>`;
  }).join(''):`<tr><td colspan="8" class="empty">Nenhum recebimento.</td></tr>`;
}
'''
text = replace_between(text, 'function renderPayments', 'function renderClauses', render_payments)

overdues = r'''function overdueLoans(){
  const now=new Date();now.setHours(0,0,0,0);
  return state.loans.filter(l=>{ if(loanTotalDue(l)<=0 || ['Cancelado','Renegociado','Excluído'].includes(l.status))return false; const d=new Date(loanCurrentDueDate(l)+'T00:00:00'); return d<now; });
}
'''
text = replace_between(text, 'function overdueLoans', 'function checkOverduePopup', overdues)

collection = r'''function renderCollection(){
  const now=new Date();now.setHours(0,0,0,0); const limit=new Date(now);limit.setDate(limit.getDate()+7);
  const rows=state.loans.filter(l=>{ const due=loanCurrentDueDate(l); const d=new Date(due+'T00:00:00'); return loanTotalDue(l)>0 && !['Cancelado','Renegociado','Excluído'].includes(l.status) && d<=limit; }).sort((a,b)=>loanCurrentDueDate(a).localeCompare(loanCurrentDueDate(b)));
  document.getElementById('collectionTable').innerHTML=rows.length?rows.map(l=>{
    const c=state.clients.find(x=>x.id===l.clientId); const due=loanCurrentDueDate(l); const d=new Date(due+'T00:00:00'); const diff=Math.floor((now-d)/86400000); const s=diff>0?'Vencido':diff===0?'Vence hoje':`Em ${Math.abs(diff)} dia(s)`; const f=loanFinancialBreakdown(l); const renewal=latestRenewal(l);
    const detail=renewal&&!f.interestActive?`<div style="font-size:11px;color:var(--primary);margin-top:3px">Principal ${brl(f.principalRemaining)} · próximos juros ${brl(f.conditionalInterest)} somente se atrasar</div>`:`<div style="font-size:11px;color:${f.overdueInterest>0?'var(--danger)':'var(--muted)'};margin-top:3px">Principal ${brl(f.principalRemaining)} · juros ${brl(f.currentInterest)}${f.overdueInterest>0?` · atraso ${brl(f.overdueInterest)}`:''}</div>`;
    return `<tr><td>${safe(c?.name||'-')}</td><td>#${l.contractNo}</td><td>${dateBR(due)}</td><td>${diff>0?diff+' em atraso':diff===0?'Hoje':Math.abs(diff)+' para vencer'}</td><td>${brl(f.total)}${detail}</td><td>${safe(c?.phone||'-')}</td><td>${badgeStatus(diff>0?'Vencido':s)}</td><td class="split"><button class="btn btn-success btn-sm" onclick="openPaymentModal('${l.id}')">Receber</button><button class="btn btn-outline btn-sm" onclick="copyCollection('${l.id}')">Copiar cobrança</button></td></tr>`;
  }).join(''):`<tr><td colspan="8" class="empty">Nenhuma cobrança para os próximos 7 dias.</td></tr>`;
}
'''
text = replace_between(text, 'function renderCollection', 'function copyCollection', collection)

copy_collection = r'''function copyCollection(id){
  const l=state.loans.find(x=>x.id===id); const c=state.clients.find(x=>x.id===l.clientId); if(!l||!c)return toast('Contrato ou cliente não encontrado.');
  const f=loanFinancialBreakdown(l); const renewal=latestRenewal(l);
  const lines=[`Olá, ${c.name}.`,'',`Segue a posição atualizada do contrato nº ${l.contractNo}:`,'',`Valor original do contrato: ${brl(f.originalPrincipal)}`,`Juros contratados no 1º ciclo (${f.rate.toFixed(2).replace('.',',')}%): ${brl(f.originalInterest)}`,`Saldo principal atual: ${brl(f.principalRemaining)}`];
  if(renewal&&!f.interestActive)lines.push(`Juros atualmente cobrados neste ciclo: ${brl(0)}`,`Próximo vencimento: ${dateBR(f.dueDate)}`,`Juros previstos para o próximo ciclo: ${brl(f.conditionalInterest)}`,`Importante: esses juros só serão cobrados se o saldo principal não for quitado até ${dateBR(f.dueDate)}.`,`Valor para quitação até o vencimento: ${brl(f.principalRemaining)}`);
  else{ lines.push(`Juros atualmente em aberto: ${brl(f.currentInterest)}`); if(f.overdueInterest>0)lines.push(`Dias em atraso: ${f.overdueDays}`,`Acréscimo por atraso: ${brl(f.overdueInterest)}`); lines.push(`Total atualizado: ${brl(f.total)}`,`Vencimento: ${dateBR(f.dueDate)}`); }
  lines.push('','Caso o pagamento já tenha sido realizado, por favor, desconsidere esta mensagem.','','Atenciosamente,','John Sistemas');
  navigator.clipboard?.writeText(lines.join(String.fromCharCode(10)));toast('Mensagem de cobrança copiada.');
}
'''
text = replace_between(text, 'function copyCollection', 'function copyLoanMessage', copy_collection)

old_notice = '<div class="notice"><b>Juros por atraso:</b> calculado somente sobre o valor dos juros do contrato. Fórmula: <b>juros ÷ 30 × dias em atraso</b>. O valor principal emprestado não entra nessa base.</div>'
new_notice = '<div class="notice"><b>Regra de ciclos:</b> ao quitar os juros de um ciclo e permanecer principal em aberto, o principal recebe novo vencimento. O próximo juros fica apenas <b>previsto</b> e só é cobrado se o principal não for quitado até esse novo vencimento. Havendo atraso, o acréscimo diário é calculado por <b>juros do ciclo ÷ 30 × dias em atraso</b>.</div>'
if old_notice in text: text=text.replace(old_notice,new_notice,1)
elif new_notice not in text: raise SystemExit('Aviso do modal de pagamento não encontrado')

text = text.replace(".sort((a,b)=>a.dueDate.localeCompare(b.dueDate)).slice(0,8);", ".sort((a,b)=>loanCurrentDueDate(a).localeCompare(loanCurrentDueDate(b))).slice(0,8);")
text = text.replace("${dateBR(l.dueDate)}</td><td>${brl(loanBalance(l))}", "${dateBR(loanCurrentDueDate(l))}</td><td>${brl(loanTotalDue(l))}")
text = text.replace("const overdue=state.loans.filter(l=>loanStatus(l)==='Vencido').reduce((a,l)=>a+loanBalance(l),0);", "const overdue=state.loans.filter(l=>loanStatus(l)==='Vencido').reduce((a,l)=>a+loanTotalDue(l),0);")

old_account = """    state.payments.filter(p=>p.loanId===l.id).forEach(p=>events.push({date:p.date,order:1,desc:`Pagamento contrato #${l.contractNo}`,debit:0,credit:Number(p.value)}));
    (Array.isArray(l.renewals)?l.renewals:[]).forEach(r=>events.push({date:r.date,order:2,desc:`Renovação do saldo contrato #${l.contractNo} - taxa ${Number(r.interestRate||0).toFixed(2).replace('.',',')}%`,debit:Number(r.interestAdded||0),credit:0}));"""
new_account = """    state.payments.filter(p=>p.loanId===l.id).forEach(p=>{
      if(paymentOverduePart(p)>0)events.push({date:p.date,order:.5,desc:`Acréscimo por atraso - contrato #${l.contractNo}`,debit:paymentOverduePart(p),credit:0});
      events.push({date:p.date,order:1,desc:`Pagamento contrato #${l.contractNo}`,debit:0,credit:Number(p.value)});
    });
    (Array.isArray(l.renewals)?l.renewals:[]).forEach(r=>{
      const activated=renewalInterestActive(r,todayISO())?renewalConditionalInterestAmount(l,r):0;
      if(activated>0)events.push({date:plusDays(r.dueDate,1),order:2,desc:`Juros do ciclo ativados após vencimento - contrato #${l.contractNo}`,debit:activated,credit:0});
    });
    const currentLate=loanOverdueInterest(l);
    if(currentLate>0)events.push({date:todayISO(),order:3,desc:`Acréscimo por atraso ainda em aberto - contrato #${l.contractNo}`,debit:currentLate,credit:0});"""
if old_account in text: text=text.replace(old_account,new_account,1)
elif 'Juros do ciclo ativados após vencimento' not in text: raise SystemExit('Trecho da conta corrente não encontrado')

text = text.replace(".reduce((a,l)=>a+loanBalance(l),0);\n\n  document.getElementById('dreBox')", ".reduce((a,l)=>a+loanTotalDue(l),0);\n\n  document.getElementById('dreBox')",1)
text = text.replace("navigator.serviceWorker.register('./sw.js?v=99'", "navigator.serviceWorker.register('./sw.js?v=100'")
INDEX.write_text(text,encoding='utf-8')

sw=SW.read_text(encoding='utf-8')
import re
sw=re.sub(r"const CACHE_NAME='john-sistemas-pwa-[^']+';","const CACHE_NAME='john-sistemas-pwa-v100-conditional-cycle-interest';",sw,count=1)
SW.write_text(sw,encoding='utf-8')

for check in ['function renewalInterestActive','interestConditional:true','Juros previstos para o próximo ciclo',"sw.js?v=100"]:
    if check not in text: raise SystemExit(f'Validação do patch falhou: {check}')
if 'john-sistemas-pwa-v100-conditional-cycle-interest' not in sw: raise SystemExit('Cache v100 não aplicado')
print('Regra condicional de juros por ciclo aplicada com sucesso.')
