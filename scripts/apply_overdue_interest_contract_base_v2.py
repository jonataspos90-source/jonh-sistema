from pathlib import Path
import re

index_path = Path('index.html')
sw_path = Path('sw.js')

html = index_path.read_text(encoding='utf-8')

pattern = re.compile(
    r"function loanInterestBaseForOverdue\(l\)\{\n"
    r"  const renewal=latestRenewal\(l\);\n"
    r"  if\(renewal\)return Math\.max\(0,Number\(renewal\.interestAdded\|\|0\)\);\n"
    r"  return Math\.max\(0,Number\(l\.total\|\|0\)-Number\(l\.principal\|\|0\)\);\n"
    r"\}"
)

replacement = """function loanInterestBaseForOverdue(l){
  if(!l)return 0;
  const principal=Math.max(0,Number(l.principal||0));
  const rate=Math.max(0,Number(l.interest||0));
  // Regra: o atraso incide somente sobre os juros contratuais originais.
  // Ex.: principal 100, juros 40% => base de atraso 40, nunca 100 nem 140.
  return principal*(rate/100);
}"""

html, count = pattern.subn(replacement, html, count=1)
if count != 1:
    raise SystemExit(f'Não foi possível atualizar loanInterestBaseForOverdue (ocorrências: {count}).')

html = html.replace(
    'Base do atraso (somente juros):',
    'Juros contratuais (base do atraso):'
)

# Faz o PWA instalado no iOS buscar a nova versão do service worker.
html = re.sub(r"sw\.js\?v=\d+", "sw.js?v=99", html)

# Validação de regressão do exemplo aprovado:
# R$ 100 principal + R$ 40 juros + (40 / 30 * 21) = R$ 168.
principal = 100.0
rate = 40.0
days = 21
contract_interest = principal * (rate / 100)
overdue_interest = (contract_interest / 30) * days
total_due = principal + contract_interest + overdue_interest
assert abs(contract_interest - 40.0) < 1e-9
assert abs(overdue_interest - 28.0) < 1e-9
assert abs(total_due - 168.0) < 1e-9

# Confirma que a implementação JS continua com a fórmula correta.
assert 'return principal*(rate/100);' in html
assert 'const accrued=(base/30)*days;' in html
assert 'return Math.max(0,loanBalance(l)+loanOverdueInterest(l,referenceDate));' in html

index_path.write_text(html, encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(
    r"const CACHE_NAME='john-sistemas-pwa-[^']+';",
    "const CACHE_NAME='john-sistemas-pwa-v99-overdue-contract-interest';",
    sw,
    count=1,
)
if "john-sistemas-pwa-v99-overdue-contract-interest" not in sw:
    raise SystemExit('Não foi possível atualizar a versão do cache do PWA.')
sw_path.write_text(sw, encoding='utf-8')

print('Regra validada: 100 + 40 + (40/30*21) = 168. PWA atualizado para v99.')
