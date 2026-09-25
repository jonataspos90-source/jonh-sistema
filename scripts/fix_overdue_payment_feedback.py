from pathlib import Path
p=Path('index.html')
s=p.read_text(encoding='utf-8')
old="""    audit('Pagamento recebido',`Contrato ${l.contractNo} - ${brl(value)} - ciclo ${cycleBefore}${renewedBalance!==null?' → '+(cycleBefore+1)+' - novo saldo '+brl(renewedBalance):' - quitado'}`);
    saveState();closeModal();renderAll();
    if(renewedBalance!==null) toast(`Pagamento parcial registrado. Ciclo ${cycleBefore+1} aberto com saldo de ${brl(renewedBalance)}.`);
    else toast(`Pagamento registrado. Contrato ${l.contractNo} quitado.`);"""
new="""    const contractSettled=contractValue>=baseBal-0.009;
    const paymentResult=renewedBalance!==null
      ?` → ${cycleBefore+1} - novo saldo ${brl(renewedBalance)}`
      :(contractSettled?' - quitado':` - juros de atraso recebidos ${brl(overdueInterestPart)}; saldo contratual ${brl(baseBal)}`);
    audit('Pagamento recebido',`Contrato ${l.contractNo} - ${brl(value)} - ciclo ${cycleBefore}${paymentResult}`);
    saveState();closeModal();renderAll();
    if(renewedBalance!==null) toast(`Pagamento parcial registrado. Ciclo ${cycleBefore+1} aberto com saldo de ${brl(renewedBalance)}.`);
    else if(contractSettled) toast(`Pagamento registrado. Contrato ${l.contractNo} quitado.`);
    else toast(`Juros de atraso registrados. O saldo contratual permanece em ${brl(baseBal)}.`);"""
if old not in s:
    raise SystemExit('Trecho de feedback do pagamento não encontrado')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('Feedback de pagamento corrigido.')
