# agentic-stack — web

Front-end do [agentic-stack](../../README.md): login, chat com o agente (resposta em streaming via SSE) e aprovação das ações que o agente pausa para confirmar, como enviar um email. Conversa com a API em [`apps/agent`](../agent) e guarda usuários e sessões no mesmo Postgres, via [Better Auth](https://www.better-auth.com).

Criado a partir do template [`nextjs-16-boilerplate`](https://github.com/felipebetts/nextjs-16-boilerplate): TypeScript estrito, Tailwind CSS v4 + shadcn/ui, testes unitários e E2E e pipeline de lint/formatação.

> ⚠️ **Este não é o Next.js "padrão".** O projeto está na versão 16, que traz mudanças de API/convenções em relação a versões anteriores. Antes de mexer em configuração do Next (`next.config.ts`, App Router, etc.), consulte `node_modules/next/dist/docs/` (ver `AGENTS.md`) em vez de assumir conhecimento de versões antigas.

## Índice

- [O que já vem configurado](#o-que-já-vem-configurado)
- [Como o app funciona](#como-o-app-funciona)
- [Requisitos](#requisitos)
- [Como rodar](#como-rodar)
- [Scripts disponíveis](#scripts-disponíveis)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Estilização e componentes de UI](#estilização-e-componentes-de-ui)
- [Testes](#testes)
- [Lint e formatação](#lint-e-formatação)
- [Git hooks (Husky)](#git-hooks-husky)
- [Documentação completa (deep dive)](#documentação-completa-deep-dive)
- [Deploy](#deploy)

## O que já vem configurado

| Área             | Ferramentas                                                             |
| ---------------- | ----------------------------------------------------------------------- |
| Framework        | Next.js 16 (App Router), React 19                                       |
| Linguagem        | TypeScript 5 (modo `strict`)                                            |
| Estilização      | Tailwind CSS v4 + shadcn/ui (`style: base-nova`, ícones Remix Icon)     |
| Componentes/UI   | `@base-ui/react`, `class-variance-authority`, util `cn`                 |
| Testes unitários | Vitest + Testing Library + jsdom                                        |
| Testes E2E       | Playwright (chromium, firefox, webkit)                                  |
| Lint             | ESLint 9 (flat config) — `eslint-config-next`, `jsx-a11y`, `check-file` |
| Formatação       | Prettier — ordenação automática de imports e de classes Tailwind        |
| Git hooks        | Husky + lint-staged (`pre-commit`) e testes unitários (`pre-push`)      |
| Ambiente         | Node fixado via `.nvmrc`, pnpm como package manager único               |
| Env vars         | Helper tipado (`src/utils/env.ts`) com validação de env obrigatória     |

Cada uma dessas áreas está documentada em detalhe em [`docs/config/`](./docs/config) — veja a seção [Documentação completa](#documentação-completa-deep-dive).

## Como o app funciona

- **Login**: `src/app/page.tsx` é um Server Component que lê a sessão do Better Auth e mostra a tela de login (`src/components/auth-form.tsx`) ou o chat (`src/components/chat-screen.tsx`). As rotas do Better Auth ficam em `src/app/api/auth/[...all]`; a config, em `src/lib/auth.ts`.
- **Token para o agent**: o plugin `jwt` do Better Auth emite um JWT EdDSA de 15 min (`/api/auth/token`) e publica as chaves em `/api/auth/jwks`. O front manda o token como `Bearer` para a API do agent, que o valida por essas chaves (`src/lib/agent/instance.ts`).
- **Chat**: `src/components/agent-chat.tsx` usa os componentes `message`, `message-scroller`, `bubble` e `marker` do shadcn. O estado vem do hook `src/lib/agent/use-agent-thread.ts`, que consome o SSE da API.
- **Aprovação**: quando o agente pausa (interrupt), `src/components/approval-card.tsx` mostra a ação (o email como rascunho, ou a lista de argumentos para ações sem formato próprio) com "Enviar"/"Recusar".
- **Contrato**: `src/lib/agent/schema.d.ts` é gerado de `../agent/openapi.json`. Mudou a API? Rode `make contract` na raiz do monorepo; nunca edite o arquivo à mão.

## Requisitos

- **Node** na versão definida em [`.nvmrc`](./.nvmrc) (`lts/jod`, Node 22 LTS). Se usar `nvm`: `nvm use`.
- **pnpm** — único package manager suportado (fixado em `package.json#packageManager`). Não use `npm` ou `yarn` neste repo.

## Como rodar

O jeito mais simples é subir tudo pela raiz do monorepo com `make dev` (Postgres, tabelas de auth, API e web). Veja o [README da raiz](../../README.md). Para rodar só o web:

```bash
# 1. instale as dependências
pnpm install

# 2. copie o template de env e troque o BETTER_AUTH_SECRET
cp .env.example .env.local

# 3. crie o schema `auth` e as tabelas do Better Auth (Postgres precisa estar de pé)
pnpm auth:migrate

# 4. suba o servidor de desenvolvimento
pnpm dev
```

Abra [http://localhost:3000](http://localhost:3000) e crie uma conta. O chat precisa da API do agent rodando em `NEXT_PUBLIC_AGENT_URL`.

As fontes do projeto (Geist Sans, Geist Mono e Instrument Sans para headings) são carregadas e otimizadas via [`next/font/google`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) em `src/app/layout.tsx`.

## Scripts disponíveis

| Comando                | O que faz                                                          |
| ---------------------- | ------------------------------------------------------------------ |
| `pnpm dev`             | Sobe o servidor de desenvolvimento (`next dev`)                    |
| `pnpm build`           | Gera o build de produção (`next build`)                            |
| `pnpm start`           | Sobe o build de produção já gerado (`next start`)                  |
| `pnpm lint`            | Roda o ESLint em todo o projeto                                    |
| `pnpm format`          | Formata todo o repositório com Prettier                            |
| `pnpm test`            | Roda os testes unitários (Vitest) uma vez                          |
| `pnpm test:watch`      | Roda os testes unitários em modo watch                             |
| `pnpm test:e2e`        | Builda a aplicação e roda os testes E2E (Playwright) contra ela    |
| `pnpm typecheck`       | Gera os tipos de rota do Next e roda o `tsc`                       |
| `pnpm auth:migrate`    | Cria o schema `auth` e as tabelas do Better Auth (idempotente)     |
| `pnpm gen:agent-types` | Gera `src/lib/agent/schema.d.ts` (prefira `make contract` na raiz) |

## Estrutura do projeto

```
├── docs/config/          # documentação de deep dive sobre cada parte do setup
├── public/                # assets estáticos
├── src/
│   ├── app/               # App Router (rotas, layout, globals.css)
│   ├── app/api/auth/      # rotas do Better Auth (inclui /api/auth/jwks e /token)
│   ├── components/        # telas do app (login, chat, aprovação)
│   ├── components/ui/     # componentes de UI (gerados via shadcn CLI)
│   ├── lib/               # auth (server/client), cliente da API do agent, utilitários
│   ├── utils/             # leitura de env vars (servidor e navegador)
│   └── tests/
│       ├── config/        # configs de Vitest e Playwright
│       ├── unit/          # testes unitários
│       └── e2e/           # specs end-to-end
├── scripts/               # ensure-auth-schema.mjs (usado pelo auth:migrate)
├── components.json        # config da CLI do shadcn/ui
├── eslint.config.mjs      # config do ESLint (flat config)
├── next.config.ts         # config do Next.js
├── postcss.config.mjs     # config do Tailwind CSS v4 (via PostCSS)
├── tsconfig.json          # config do TypeScript
└── .prettierrc.json       # config do Prettier
```

Arquivos e pastas de código seguem `KEBAB_CASE` (imposto pelo ESLint) e pastas dentro de `src/app` seguem a convenção do App Router — veja [`docs/config/lint-formatacao.md`](./docs/config/lint-formatacao.md).

## Variáveis de ambiente

- [`.env.example`](./.env.example) é o template versionado; qualquer `.env*` real (`.env.local`, etc.) é ignorado pelo git.
- Envs do servidor ficam em [`src/utils/env.ts`](./src/utils/env.ts), via `requireEnv`, que lança erro se uma env obrigatória não estiver definida. Envs do navegador (`NEXT_PUBLIC_*`) ficam em [`src/utils/public-env.ts`](./src/utils/public-env.ts), lidas de forma literal, porque o Next só embute no bundle acessos como `process.env.NEXT_PUBLIC_X`.

| Variável                | Onde      | Para quê                                                                                    |
| ----------------------- | --------- | ------------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_AGENT_URL` | navegador | URL da API do agent. Embutida no build                                                      |
| `DATABASE_URL`          | servidor  | Postgres (o mesmo do agent); tabelas no schema `auth`                                       |
| `BETTER_AUTH_SECRET`    | servidor  | Segredo do Better Auth (`openssl rand -base64 32`)                                          |
| `BETTER_AUTH_URL`       | servidor  | URL pública deste app. Precisa ser igual ao `AUTH_URL` do agent, senão ele recusa os tokens |

Sem as envs do servidor, `pnpm build` falha ao carregar a rota de auth.

## Estilização e componentes de UI

O projeto usa **Tailwind CSS v4** (configurado via CSS em `src/app/globals.css`, sem `tailwind.config.js`) e **shadcn/ui** para componentes.

Regra importante deste projeto: **reutilize componentes já existentes em `src/components/ui` antes de criar algo novo**; se o componente não existir, **instale-o via CLI do shadcn** em vez de escrevê-lo à mão:

```bash
pnpm dlx shadcn@latest add <componente>
```

Detalhes completos (tokens de tema, dark mode, anatomia de um componente, fluxo recomendado) em [`docs/config/estilizacao.md`](./docs/config/estilizacao.md).

## Testes

- **Unitários**: Vitest + Testing Library, rodando em `jsdom`. Config em `src/tests/config/vitest.config.mts`; testes em `src/tests/unit`.
- **E2E**: Playwright, rodando em chromium/firefox/webkit contra um build de produção subido automaticamente. Config em `src/tests/config/playwright.config.ts`; specs em `src/tests/e2e`.

Detalhes completos em [`docs/config/testes.md`](./docs/config/testes.md).

## Lint e formatação

- **ESLint** (flat config, `eslint.config.mjs`): regras do Next.js (`core-web-vitals`, TypeScript), `jsx-a11y`, e convenções de nomenclatura de arquivos/pastas via `eslint-plugin-check-file`.
- **Prettier** (`.prettierrc.json`): sem ponto e vírgula, aspas simples, ordenação automática de imports (`@trivago/prettier-plugin-sort-imports`) e de classes Tailwind (`prettier-plugin-tailwindcss`).
- **EditorConfig** e **VS Code** (`.vscode/settings.json`) já configurados para formatar e aplicar fixes do ESLint ao salvar.

Detalhes completos em [`docs/config/lint-formatacao.md`](./docs/config/lint-formatacao.md).

## Git hooks (Husky)

- **`pre-commit`**: roda `lint-staged` (ESLint `--fix` + Prettier) apenas nos arquivos `.ts`/`.tsx` staged.
- **`pre-push`**: roda `pnpm test` (testes unitários) e bloqueia o push se algum teste falhar.
- Instalados automaticamente pelo script `prepare` do `package.json` após `pnpm install` — não é necessário nenhum passo manual.

Detalhes completos em [`docs/config/husky.md`](./docs/config/husky.md).

## Documentação completa (deep dive)

Para entender exatamente _como e por quê_ cada parte do stack está configurada (não só o que está instalado), consulte:

- [`docs/config/stack-geral.md`](./docs/config/stack-geral.md) — Node/pnpm, scripts, Next.js, TypeScript e variáveis de ambiente.
- [`docs/config/testes.md`](./docs/config/testes.md) — Vitest e Playwright.
- [`docs/config/estilizacao.md`](./docs/config/estilizacao.md) — Tailwind CSS v4, shadcn/ui e o fluxo de reuso/instalação de componentes.
- [`docs/config/lint-formatacao.md`](./docs/config/lint-formatacao.md) — ESLint, Prettier e EditorConfig.
- [`docs/config/husky.md`](./docs/config/husky.md) — hooks de `pre-commit` e `pre-push`.

## Deploy

Vercel com root directory `apps/web`, com as quatro envs acima definidas (a URL pública em `BETTER_AUTH_URL`, e a da API em `NEXT_PUBLIC_AGENT_URL`). Rode `pnpm auth:migrate` contra o banco de produção antes do primeiro deploy e ao atualizar o Better Auth. Do lado do agent, `AUTH_URL` deve ser a URL pública deste app e `CORS_ORIGINS` deve incluí-la.
