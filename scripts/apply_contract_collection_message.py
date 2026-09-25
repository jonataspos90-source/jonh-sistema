from pathlib import Path
import re

path = Path("index.html")
source = path.read_text(encoding="utf-8")

pattern = re.compile(
    r"const msg=`Olá, \$\{c\.name\}\..*?Caso o pagamento já tenha sido realizado, desconsidere esta mensagem\.`;",
    re.S,
)

replacement = """const msg=[
    `Olá, ${c.name}.`,
    '',
    `Passando para lembrar sobre o contrato nº ${l.contractNo}.`,
    '',
    `Saldo em aberto: ${brl(loanBalance(l))}`,
    `Vencimento: ${dateBR(l.dueDate)}`,
    '',
    'Caso o pagamento já tenha sido realizado, por favor, desconsidere esta mensagem.',
    '',
    'Atenciosamente,',
    'John Sistemas'
  ].join('\\n');"""

updated, count = pattern.subn(replacement, source, count=1)
if count != 1:
    raise SystemExit(f"Template de cobrança não encontrado ou ambíguo: {count} ocorrência(s).")

path.write_text(updated, encoding="utf-8")
print("Mensagem de cobrança atualizada com sucesso.")
