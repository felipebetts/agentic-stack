# Notas e decisões do projeto

Log cronológico de decisões, aprendizados e mudanças não-óbvias que não cabem em nenhum doc de `docs/config/` (que são organizados por área de tooling, não por linha do tempo). Serve como "memória" do projeto entre sessões — antes de investigar algo do zero, olhe aqui.

Formato de cada entrada: data, o que mudou/foi decidido, e o porquê (quando relevante).

## Como usar

- Ao tomar uma decisão não-óbvia, descobrir uma restrição, ou fazer uma mudança que outra sessão precisaria saber para não redescobrir do zero, adicione uma entrada aqui (ou atualize o `docs/config/*.md` relevante, se for sobre _como uma parte do stack está configurada_).
- Entradas antigas que não são mais relevantes (decisão revertida, contexto que não existe mais) devem ser removidas ou marcadas como obsoletas, não acumuladas indefinidamente.

## Entradas

- **2026-09-17** — Criado este arquivo e o `CLAUDE.md` na raiz do projeto (antes só existia `@AGENTS.md` como referência). `CLAUDE.md` agora documenta comandos, arquitetura e a convenção de manter `docs/` atualizado.
- **2026-10-01** — Projeto criado a partir do template `nextjs-16-boilerplate` para substituir o front antigo (Next 15, npm, CSS puro) do `agentic-stack`, mantendo as mesmas features: login com Better Auth, chat com o agent via SSE, aprovação de ações (interrupts). O chat usa os componentes `message`/`message-scroller`/`bubble`/`marker` do shadcn, por pedido do usuário.
- **2026-10-01** — Envs divididas em `env.ts` (servidor) e `public-env.ts` (navegador): `requireEnv` lê `process.env[name]`, e o Next só embute `NEXT_PUBLIC_*` em acessos literais. Detalhes em `docs/config/stack-geral.md`.
- **2026-10-01** — O Better Auth descobre o schema pelo `current_schema()`. Se o `search_path` apontar para um schema que não existe, a CLI cria as tabelas em `public` sem avisar; por isso `pnpm auth:migrate` cria o schema `auth` antes (`scripts/ensure-auth-schema.mjs`). Sem `search_path` fixo, o padrão `"$user", public` mandava as tabelas para o schema `agent` (usuário do banco de dev = `agent`).
- **2026-10-01** — O `spinner.tsx` gerado pelo shadcn foi tipado com `ComponentProps<RemixiconComponentType>`: o original (`ComponentProps<'svg'>`) inclui `children`, que os ícones do Remix não aceitam, e quebrava o typecheck. Se regenerar o componente pela CLI, reaplique.
