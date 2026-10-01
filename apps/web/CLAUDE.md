# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Project

Web front-end of **agentic-stack** (lives in `apps/web` of the monorepo; the Python agent API is in `../agent`). Users sign in, chat with a LangGraph agent that streams over SSE, and approve or refuse actions the agent pauses on (e.g. sending an email) before they run. Stack: Next.js 16 App Router, TypeScript strict, Tailwind CSS v4 + shadcn/ui, Better Auth on Postgres, Vitest + Playwright, ESLint + Prettier. Started from the `felipebetts/nextjs-16-boilerplate` template.

- **Auth**: Better Auth (`src/lib/auth.ts`, route `src/app/api/auth/[...all]`), email/password, tables in the Postgres schema `auth` (created by `pnpm auth:migrate`). The `jwt` plugin issues short-lived EdDSA tokens that the client sends to the agent API as `Bearer`; the agent validates them against `/api/auth/jwks`. `BETTER_AUTH_URL` must equal the agent's `AUTH_URL`.
- **Agent API client**: `src/lib/agent/` — `schema.d.ts` is generated from `../agent/openapi.json` (run `make contract` at the monorepo root, never edit by hand); `client.ts` (typed fetch + SSE), `use-agent-thread.ts` (React hook), `chat-state.ts` (pure state helpers, unit tested), `instance.ts` (token caching).
- **UI**: `src/app/page.tsx` is a Server Component that reads the session and renders `AuthForm` or `ChatScreen`. The chat uses shadcn `message`, `message-scroller`, `bubble` and `marker`; `approval-card.tsx` renders pending approvals.

## Commands

pnpm is the only supported package manager (pinned via `packageManager` in `package.json`) — never use `npm`/`yarn` in this repo.

- `pnpm install` — install deps
- `pnpm dev` / `pnpm build` / `pnpm start` — dev server / production build / serve build
- `pnpm lint` — ESLint (flat config)
- `pnpm format` — Prettier, writes across the whole repo
- `pnpm test` — unit tests once (Vitest)
- `pnpm test:watch` — unit tests in watch mode
- `pnpm test:e2e` — Playwright E2E; builds and boots the app on port 3100 automatically first, so it's much slower than the unit suite
- Single unit test file: `pnpm test src/tests/unit/page.test.tsx` (Vitest CLI filtering, e.g. `-t <name>`, works the same way through this script)
- Single e2e spec: `pnpm test:e2e src/tests/e2e/home.spec.ts`

## Architecture

- **Test layout is non-default and deliberate**: configs live in `src/tests/config/` (`vitest.config.mts`, `playwright.config.ts`), unit tests in `src/tests/unit/`, e2e specs in `src/tests/e2e/` — none at the repo root. Always run tests through the `pnpm test*` scripts; invoking `vitest`/`playwright` directly without `--config src/tests/config/...` won't resolve correctly.
- **Tailwind v4 has no `tailwind.config.js`**: all theme tokens (colors, radius, dark-mode variant) live in `src/app/globals.css` under `@theme inline`, `:root`, `.dark`. Change the design system there, not via ad hoc utility classes scattered through components.
- **shadcn/ui is on `base-nova`**, which is built on `@base-ui/react` (not Radix) — that's why `@base-ui/react` (not `@radix-ui/*`) is the primitive layer under `src/components/ui`. `lucide-react` is a leftover from `create-next-app`; new components should use `@remixicon/react` per `components.json`'s `iconLibrary`.
- **UI components are meant to be generated, not hand-written**: reuse what's already in `src/components/ui` first; if missing, install via `pnpm dlx shadcn@latest add <component>` (reads `components.json`); only hand-write as a last resort, following the pattern in the existing `button.tsx` (base-ui primitive + `cva` variants + `cn` + `data-slot`).
- Path alias `@/*` → `src/*`, matching both `tsconfig.json` and the shadcn `aliases` in `components.json`. If `src/components/ui` or `src/lib` ever move, update `components.json` too or the shadcn CLI will generate files in the wrong place.
- Server env vars are centralized in `src/utils/env.ts` via `requireEnv(name, optional?)`; browser env vars (`NEXT_PUBLIC_*`) live in `src/utils/public-env.ts` as literal `process.env.NEXT_PUBLIC_X` reads, because Next only inlines literal accesses. Never import `env.ts` from Client Components.
- `pnpm typecheck` runs `next typegen` before `tsc` (route helper types like `LayoutProps` come from `.next/types`).
- Husky hooks: `.git` lives at the monorepo root, so `prepare` is `cd ../.. && husky apps/web/.husky` and the hooks `cd apps/web` first.
- File/folder naming is enforced by ESLint (`eslint-plugin-check-file`): `.ts`/`.tsx` files must be `KEBAB_CASE`; folders under `src/app/**` must follow Next's App Router casing (`(group)`, `[slug]`, `[...catchAll]`).
- Deep-dive docs for each area of the stack (the _why_ behind non-default config choices) live in `docs/config/`: `stack-geral.md` (Node/pnpm/Next/TS/env), `testes.md` (Vitest/Playwright), `estilizacao.md` (Tailwind/shadcn), `lint-formatacao.md` (ESLint/Prettier). Read the relevant one before making non-trivial changes in that area.

## Keeping docs current

- `docs/config/*.md` is the source of truth for _how and why_ each part of the stack is configured. When you change tooling/config non-cosmetically (test setup, lint rules, styling system, env handling, Next.js config, package manager), update the matching file there — or add a new one if the change doesn't fit an existing doc — rather than letting the docs drift from reality.
- `docs/notas.md` is a chronological log for decisions, constraints, and non-obvious learnings that don't belong in a specific `docs/config/` area doc. When you learn or decide something a future session would otherwise have to rediscover from scratch, add a dated entry there.
- Update this file (`CLAUDE.md`) itself when the architecture, commands, or conventions described here change — it should never describe a state of the repo that no longer exists.
