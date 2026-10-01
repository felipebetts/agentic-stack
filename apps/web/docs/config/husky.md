# Git hooks (Husky + lint-staged)

Os hooks de Git ficam em `.husky/` (versionado) e são instalados automaticamente via script `prepare` do `package.json`, que roda `husky` logo após o `pnpm install`.

```
.husky/
├── _/            # runtime interno do Husky (gerado, não editar)
├── pre-commit    # roda antes de cada commit
└── pre-push      # roda antes de cada push
```

## `prepare` (`package.json`)

```json
{
  "scripts": {
    "prepare": "cd ../.. && husky apps/web/.husky"
  }
}
```

- Este app vive em `apps/web` dentro do monorepo `agentic-stack`, e o `.git` fica na raiz do monorepo. Por isso o `prepare` sobe até a raiz e aponta o Husky para `apps/web/.husky` (o `husky` sozinho só funciona quando o `package.json` está na raiz do repositório).
- Pelo mesmo motivo, o Git executa os hooks a partir da raiz do monorepo: os dois hooks começam com `cd apps/web`.
- Sem repositório git, o `prepare` só imprime `.git can't be found` e segue; os hooks passam a valer depois do `git init`, rodando `pnpm install` de novo.
- pnpm executa `prepare` automaticamente depois de `pnpm install`, o que aponta `core.hooksPath` do Git para `apps/web/.husky/` e garante que os hooks fiquem ativos para qualquer pessoa que clonar o repo — não é necessário rodar `husky install` manualmente.
- Se os hooks parecerem não estar rodando (ex.: após um clone novo), rode `pnpm install` de novo para reexecutar o `prepare`.

## `pre-commit`

```bash
cd apps/web
pnpm exec lint-staged
```

Roda `lint-staged`, que só aplica lint/formatação nos arquivos **staged** (evita reformatar o repo inteiro a cada commit). A config vive em `package.json`:

```json
{
  "lint-staged": {
    "**/*.{ts,tsx}": ["eslint --fix --cache", "prettier --write"]
  }
}
```

- Só afeta arquivos `.ts`/`.tsx` staged.
- `eslint --fix --cache` primeiro (corrige o que der para corrigir automaticamente, usando cache para ser mais rápido) e `prettier --write` depois — mesma ordem de responsabilidade descrita em [`lint-formatacao.md`](./lint-formatacao.md) (Prettier cuida de estilo, ESLint de regras de código).
- Se o ESLint encontrar um erro que não pode corrigir sozinho (`--fix` não resolve), o commit é bloqueado até o problema ser corrigido manualmente.

## `pre-push`

```bash
cd apps/web

echo "🧪 Executando testes antes do push..."

pnpm test

echo "✅ Todos os testes passaram! Push permitido."
```

- Roda a suíte de testes unitários (Vitest, ver [`testes.md`](./testes.md)) antes de permitir o push.
- Se `pnpm test` falhar (exit code diferente de zero), o push é abortado — os testes precisam passar localmente antes de subir código para o remoto.
- Só roda os testes unitários (`pnpm test`), não os E2E (`pnpm test:e2e`) — o E2E builda a aplicação inteira e é mais lento, não é adequado para rodar em todo push local.

## Pulando os hooks (uso pontual)

Em situações excepcionais, os hooks podem ser pulados com `--no-verify`:

```bash
git commit --no-verify
git push --no-verify
```

Evite usar isso como rotina — os hooks existem para pegar problemas de lint/formatação e testes quebrados antes que cheguem ao remoto.

## Resumo prático

| Hook         | Comando                                                   | Quando bloqueia                      |
| ------------ | --------------------------------------------------------- | ------------------------------------ |
| `pre-commit` | `npx lint-staged` (ESLint + Prettier nos arquivos staged) | Erro de lint que `--fix` não resolve |
| `pre-push`   | `pnpm test`                                               | Algum teste unitário falha           |
