# Contrato da API (OpenAPI → TypeScript)

Os tipos que o web usa para falar com o agent são gerados a partir dos schemas Pydantic do agent. Os dois arquivos gerados ficam versionados, e o CI quebra se eles ficarem desatualizados.

```
apps/agent/src/agent/api/schemas.py      (fonte: modelos Pydantic)
        │  scripts/export_openapi.py
        ▼
apps/agent/openapi.json                  (gerado, commitado)
        │  openapi-typescript (pnpm gen:agent-types)
        ▼
apps/web/src/lib/agent/schema.d.ts       (gerado, commitado)
        │
        ▼
apps/web/src/lib/agent/types.ts          (aliases usados pelo app: StreamEvent, MessageOut…)
```

## Fluxo de trabalho

Mudou um schema em `api/schemas.py` ou uma rota?

```bash
make contract        # regenera openapi.json e schema.d.ts
make test            # o typecheck do web acusa o que quebrou no front
```

Commite `openapi.json` e `schema.d.ts` juntos com a mudança. **Nunca edite os dois à mão.**

`make check-contract` roda `make contract` e depois `git diff --exit-code` nos dois arquivos. Só funciona dentro de um repositório git.

## Detalhes não óbvios

- **Exportar sem subir nada**: `scripts/export_openapi.py` define `OPENROUTER_API_KEY` e `DATABASE_URL` falsos e chama `create_app().openapi()`. Não precisa de banco nem de chave.
- **Eventos SSE no OpenAPI**: o FastAPI não descreve o corpo de um stream SSE. `api/main.py` (`_install_openapi`) injeta a union `StreamEvent` em `components.schemas`, e as rotas de stream a referenciam como resposta `text/event-stream`. É daí que o front tira a _discriminated union_ (`switch (ev.event)` tipado).
- **Campos com default saem obrigatórios**: os modelos de resposta herdam de `_Out`, com `json_schema_serialization_defaults_required=True`. Sem isso, todo campo com default viraria opcional no TypeScript, embora sempre venha no JSON. É também o que torna `event` obrigatório em cada evento SSE.
- **Prettier não formata o `schema.d.ts`**: ele está no `.prettierignore` do web. Se fosse reformatado, deixaria de ser idêntico ao que o gerador produz e o `check-contract` falharia.
- **Erros**: respostas de erro seguem `ErrorOut` (`{code, message}`) dentro de `detail`. O client do web (`src/lib/agent/client.ts`) converte isso em `AgentApiError(status, code, message)`.

## O client do web

- `client.ts`: `fetch` tipado para cada rota. Os streams usam `fetch` + `parseSSE` (`sse.ts`) em vez de `EventSource`, que não suporta POST nem headers (e o token vai no header).
- `use-agent-thread.ts`: hook React que consome os eventos e mantém mensagens, interrupt pendente e status.
- `chat-state.ts`: funções puras (acumular tokens, substituir a mensagem parcial pela final, reconhecer pedidos de aprovação), cobertas por testes unitários.
