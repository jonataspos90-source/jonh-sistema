# John Sistemas · Engenharia de Custos e Produção

Aplicação web full-stack com **Node.js 20+, Express, PostgreSQL, JWT, bcryptjs, Zod, decimal.js** e interface HTML5/CSS/JavaScript responsiva, sem dependências de CDN. Todos os valores em reais, telas em português (Brasil).

## O que já está implementado

- Primeiro acesso cria **um único administrador**; login JWT com expiração de 8 horas. Cadastros de usuários administradores, operadores e perfis apenas leitura. Senhas armazenadas com bcrypt (12 rounds). JWT fica na `sessionStorage`, não em `localStorage`, para reduzir persistência no cliente. Proteja o ambiente com HTTPS.
- Produtos multi-classificação: **Produto Acabado, Revenda, Insumo, Embalagem, Uso e Consumo e Subproduto**, inclusive combinações de flags. Cadastro de embalagem de compra (pote, caixa, pacote etc.), conteúdo numérico (`500 g`, `2 L`, `12 un`), preço, FC, teste PB/PL, estoque mínimo e preço praticado.
- Cálculo em unidade base única (`kg`, `L`, `un`). Compra de pote de 500 g por R$ 12 → R$ 24/kg; FC = PB/PL; custo real por kg = custo base × FC. Estoque guarda a **quantidade bruta efetivamente adquirida**.
- Fichas técnicas vinculadas a produtos acabados ou subprodutos, composição dinâmica em unidades base, rendimento final, preço sugerido, margem de contribuição **ou** markup com definição explícita, preços praticados e bloqueio de ciclos de receitas (A → B → A).
- Produção **transacional**: verifica saldos com `FOR UPDATE`, consome `quantidade líquida × FC × fator do lote` para cada insumo e dá entrada no produto produzido, tudo dentro de `BEGIN/COMMIT` — ou nada acontece. Subprodutos são produzidos e estocados antes de serem usados por outra ficha.
- Compras com atualização de custo médio ponderado; vendas registram receita e custo contábil no momento da saída; ajustes e perdas exigem justificativa. Saldo não fica negativo. Kardex registra saldo anterior, variação, saldo posterior, tipo, custo, usuário, data e identificador de lote.
- Dashboard com estoque valorizado, alertas de mínimo, fichas ativas e custos sem atualização há mais de 30 dias.
- Relatórios de margens por item, valoração de estoque, curva ABC por receita/custo de vendas (com período) ou **valor de estoque identificado como tal** quando não há vendas; cenários de +N% uniforme no custo dos ingredientes.
- Busca por nome, filtro por classificação, layout para desktop/mobile, notificações de sucesso/erro e formulários com validação no servidor.

## Inicialização local (com Docker para o banco)

1. Instale **Node.js 20 ou 22**, **npm** e **Docker**.
2. Dentro da pasta do projeto, execute:

   ```bash
   cp .env.example .env
   node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
   ```

3. Edite `.env` e substitua `JWT_SECRET` pelo valor aleatório exibido no terminal. O servidor recusa a chave de exemplo. Depois execute:

   ```bash
   docker compose up -d postgres
   npm install
   npm run db:migrate
   npm start
   ```

   Abra **http://localhost:3000**. No primeiro acesso, cadastre o administrador com senha de pelo menos **10 caracteres** e informe a chave `BOOTSTRAP_SECRET` configurada no servidor. Não existe senha fixa de demonstração.
4. Para desenvolvimento com reinicialização automática, use `npm run dev`.
5. Validação de sintaxe: `npm run check`. Testes de unidade: `npm test`.

**Windows:** copie `.env.example` para `.env` pelo Explorador de Arquivos, ou use `copy .env.example .env` no CMD. Mantenha o PostgreSQL em funcionamento.

### Utilizar um PostgreSQL existente, Neon ou Railway

Substitua `DATABASE_URL` no `.env` pela string de conexão PostgreSQL do provedor e rode `npm run db:migrate`. Configure `JWT_SECRET` (aleatória, 32+ caracteres) e `BOOTSTRAP_SECRET` (chave secreta para permitir apenas ao responsável criar o primeiro administrador) pelo gestor de segredos do servidor, nunca no GitHub. Para PostgreSQL gerenciado que exija TLS, configure corretamente os certificados/TLS do provedor; há opção `PGSSL=true` no código, com validação do certificado. Evite `rejectUnauthorized:false`.

Para hospedar a aplicação no Railway, publique **esta pasta** como serviço Node.js, configure `DATABASE_URL`, `JWT_SECRET`, `BOOTSTRAP_SECRET`, `NODE_ENV=production` e faça a migração antes de iniciar. O servidor expõe a interface e a API na mesma origem e escuta `PORT` definido pelo ambiente.

Não faça commit do `.env`; o `.gitignore` já protege esse arquivo. Configure HTTPS, políticas de backup e logs centralizados antes do uso comercial.

## Estrutura

```
john-sistemas/
├── public/
│   ├── index.html                # interface, primeiro acesso e autenticação
│   ├── css/styles.css            # design system responsivo dark + verde
│   └── js/app.js                 # módulos, navegação, formulários, chamadas API
├── src/
│   ├── server.js                 # Express, headers e rotas
│   ├── db.js                     # Pool PostgreSQL e transações
│   ├── migrate.js                # instalação do esquema SQL
│   ├── middleware/auth.js        # JWT, sessão, papéis
│   ├── services/math.js          # conversões e precisão decimal
│   ├── services/costing.js       # composição, custo recursivo e anti-ciclos
│   └── routes/
│       ├── auth.js               # bootstrap, login, usuários
│       ├── products.js           # CRUD de produtos
│       ├── recipes.js            # fichas técnicas
│       ├── stock.js              # compras, vendas, perdas, produção, Kardex
│       └── reports.js            # KPIs e relatórios
├── sql/001_initial.sql
├── tests/math.test.js
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── package.json
```

## Exemplos de regras

| Regra | Exemplo | Resultado |
|---|---|---|
| Conversão | 500 g por R$ 12,00 | **R$ 24,00/kg** |
| FC após limpeza | 1 kg de alcatra por R$ 35, 750 g de rendimento | FC 1,333333; **R$ 46,67/kg líquido** |
| Consumo de ficha | 200 g **líquidos** da alcatra anterior | 266,667 g baixados do estoque bruto; custo **R$ 9,33** |
| Margem de contribuição de 30% | Custo unitário R$ 70 | Venda sugerida **R$ 100** (`70 / 0,7`) |
| Markup de 30% | Custo unitário R$ 70 | Venda sugerida **R$ 91** (`70 × 1,3`) |
| Molho base intermediário | Lote custa R$ 32,80, rende 4 kg | **R$ 8,20/kg** |
| Venda 2 un a R$ 25 | Saldo reduz em 2; custo vigente R$ 14/un | Receita R$ 50; custo registrado R$ 28 |

### Convenções importantes

**Unidades:** produtos têm uma unidade dimensional fixa (`kg`, `L` ou `un`). A embalagem de compra pode ter conteúdo em `mg/g/kg`, `ml/L` ou `un`. Não é permitido mudar a dimensão de um produto que já tenha ficha ou movimento. Para receitas, informe insumos em **quantidades líquidas** das respectivas unidades base. Se não houver perdas, FC = 1. Para a saída real, o FC converte de líquido para bruto. A saída de subprodutos consome a quantidade bruta do estoque intermediário (em geral FC = 1).

**Custos:** a ficha é **teórica / custo de reposição estimado**, usando o último custo de compra cadastrado (reposição), ou o custo médio apenas quando o preço de compra é zero; para subprodutos com ficha, a referência é a composição atual da receita-mãe. O **valor contábil em estoque** é sempre `saldo × custo médio ponderado registrado` e a produção entra pelo custo real dos componentes baixados. Assim, variações futuras de custo não reescrevem o custo histórico do Kardex.

**Margem:** a opção “margem de contribuição” usa `preço = custo ÷ (1 − margem%)`; a opção “markup” usa `preço = custo × (1 + markup%)`. A contribuição calculada considera **somente custos diretos de insumos e embalagens**; tributos, taxas de marketplace, encargos, salários indiretos, frete e custos fixos ainda não têm parametrização financeira própria. Sem essas parcelas, **não se deve apresentar a margem como lucro líquido**.

**Curva ABC:** quando existe histórico de vendas no período, classifica por receita de venda ou custo das vendas. Sem registros, o relatório muda explicitamente para a valoração de estoque para não afirmar que houve faturamento. A categoria segue os limiares acumulados de 80%/95%, com itens indivisíveis.

**Segurança e consistência:** a API exige JWT nas rotas privadas; perfis de consulta não escrevem. Nunca edite o estoque diretamente na tabela `products`: use as operações transacionais da API. A aplicação tem proteções iniciais (hash, validação, rate limit do login, CSP), mas produção corporativa deve passar por revisão de segurança, testes E2E com banco real, LGPD, backup, observabilidade, controle de sessão e políticas de recuperação.

## API (rotas principais)

- `POST /api/auth/bootstrap`, `POST /api/auth/login`, `GET /api/auth/me`, `GET/POST/PATCH /api/auth/users`
- `GET/POST /api/products`, `PUT/DELETE /api/products/:id`
- `GET/POST /api/recipes`, `PUT/DELETE /api/recipes/:productId`
- `GET /api/stock/balances`, `GET /api/stock/movements`
- `POST /api/stock/purchase`, `/sale`, `/adjust`, `/production`
- `GET /api/reports/dashboard`, `/margins`, `/valuation`, `/abc`, `/sensitivity`
- `GET /api/health`

**Exemplo de compra** (após obter JWT do login):

```http
POST /api/stock/purchase
Authorization: Bearer SEU_TOKEN
Content-Type: application/json

{"productId":1,"packages":2,"purchasePrice":12,"reason":"Compra NF-001"}
```

**Exemplo de produção** (ingredientes no estoque, ficha ativa):

```http
POST /api/stock/production
Authorization: Bearer SEU_TOKEN
Content-Type: application/json

{"productId":4,"outputQty":2.5,"reason":"Lote manhã"}
```

## Limitações conscientes desta primeira versão

- Autenticação JWT com armazenamento em `sessionStorage` (em produção mais exigente, migrar para cookies `httpOnly`, refresh tokens e CSRF); não há recuperação de senha por e-mail ou MFA.
- Ainda não há ordens de compra com fornecedores, impostos, custo de mão de obra, reprocessamento, inventário cíclico por lote/validade, multiempresa, relatórios exportados em PDF, nem conciliação fiscal. Não simula sincronia automática com sistemas de pedidos de terceiros.
- `npm test` cobre o **motor matemático** e detecção de ciclos. Testes de integração reais exigem PostgreSQL de teste e deverão ser adicionados antes de entrar em produção.
- O projeto usa CSS próprio (sem CDN), em vez de Tailwind em tempo de execução, para abrir rápido e funcionar com CSP restritiva. Pode ser migrado para uma compilação Tailwind sem mudar a API.

