# John Sistema — Precificação e Gestão Financeira

Aplicativo web em português para formação do preço de venda, custos e controles financeiros, com conceitos de precificação divulgados pelo Sebrae.

## Abrir o aplicativo

Abra `index.html` neste diretório em um navegador. A aplicação usa Tailwind CSS e Font Awesome via CDN; é necessária conexão com a internet para esses recursos visuais.

**Acesso demonstrativo:** `admin@johnsistema.com` / `123456`.

## Estado inicial e zeramento

- A versão inicia sem lançamentos ou cadastros fictícios.
- Em **Configurações e dados**, use a função **Zerar todos os dados** e confirme digitando `ZERAR`, se quiser limpar registros do navegador.
- É possível exportar um backup JSON antes de zerar e importá-lo posteriormente.
- Os dados são salvos apenas no `localStorage` do navegador/dispositivo usado. **Não há banco de dados ou sincronização entre dispositivos**.

## Atenção para uso real

O login é demonstrativo e funciona somente no JavaScript do navegador: **não protege os dados como uma autenticação de produção**. Não use para dados financeiros sensíveis ou usuários reais sem backend, autenticação segura, backup automatizado e isolamento dos dados.

Este projeto **não é um aplicativo oficial do Sebrae**, apenas utiliza conceitos de formação de preço em materiais educacionais do Sebrae.

O diretório `precificacao/` foi adicionado sem alterar o aplicativo principal deste repositório.
