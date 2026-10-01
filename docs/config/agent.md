# Agent (grafo LangGraph + API FastAPI)

Como o `apps/agent` está montado: o grafo, a ligação com o LLM via OpenRouter, a API HTTP e a tradução do stream do LangGraph para SSE. Persistência e locks estão em [`banco-de-dados.md`](./banco-de-dados.md); autenticação, em [`autenticacao.md`](./autenticacao.md).

## Camadas

```
src/agent/
├── graph/          # LangGraph puro: não sabe que HTTP existe
│   ├── state.py    # AgentState (MessagesState + campos futuros)
│   ├── tools.py    # tools; aprovação humana via interrupt()
│   ├── prompts.py  # SYSTEM_PROMPT
│   ├── builder.py  # build_graph(checkpointer, llm) + STREAMING_NODES
│   └── studio.py   # entry point do `langgraph dev`
├── api/            # FastAPI: auth, rotas, serialização, SSE
├── persistence/    # pool Postgres, migrations, threads, advisory locks
├── llm.py          # ChatOpenAI apontando para o OpenRouter
├── observability.py# callbacks do Langfuse (opcional)
└── config.py       # Settings (pydantic-settings, lê .env)
```

A separação é deliberada: `build_graph(checkpointer, llm)` recebe as dependências por parâmetro. Os testes montam o grafo com um LLM falso e um `InMemorySaver`, sem rede nem Postgres, e o `langgraph dev` monta sem checkpointer (o servidor de dev injeta o dele).

## O grafo

`builder.py` monta o ciclo clássico de agente com tools:

```
START → agent ──(tool_calls?)──▶ tools ──▶ agent → … → END
```

- **`agent`**: chama o LLM com `SYSTEM_PROMPT` + histórico, com as tools ligadas (`bind_tools(TOOLS)`).
- **`tools`**: `ToolNode(TOOLS)`; `tools_condition` decide se a última resposta tem tool calls.
- **`STREAMING_NODES = {"agent"}`**: só os tokens desse nó viram eventos `token` no SSE. Se criar nós que chamam LLM mas não devem aparecer para o usuário (ex.: um classificador), deixe-os fora desse conjunto.
- **`AgentState`** é um `MessagesState`. Campos novos adicionados ali são persistidos pelo checkpointer a cada passo.

### Aprovação humana (interrupts)

`send_email` em `tools.py` chama `interrupt({...})` antes de agir. O grafo pausa, o estado fica salvo no checkpoint e o cliente recebe um evento `interrupt` com o valor:

```json
{
  "type": "approval",
  "action": "send_email",
  "args": { "to": "...", "subject": "...", "body": "..." }
}
```

O front reconhece `type: "approval"` e mostra o cartão de aprovação. A resposta volta por `POST /runs/resume` como `Command(resume=...)`, e o `interrupt()` passa a retornar esse valor (`{"approved": true}` ou `{"approved": false, "reason": "..."}`).

**Regra importante**: no resume, a tool roda de novo **desde o início**. Nada com efeito colateral pode vir antes do `interrupt()`, senão executa duas vezes.

Para criar uma tool com aprovação, siga o mesmo formato de payload. O front mostra um cartão genérico (lista de argumentos) para ações que não têm formato próprio em `apps/web/src/components/approval-card.tsx`.

## LLM (OpenRouter)

`llm.py` devolve um `ChatOpenAI` apontando para `https://openrouter.ai/api/v1`:

- **`provider.require_parameters: true`**: o OpenRouter só roteia para providers que suportam todos os parâmetros enviados (tools, `response_format`). Sem isso, o mesmo modelo pode cair num provider que ignora tool calling.
- **`OPENROUTER_PROVIDER_ORDER`** (opcional) fixa a ordem de providers; `OPENROUTER_ALLOW_FALLBACKS` controla se pode sair dela.
- Headers `HTTP-Referer` (`APP_URL`) e `X-Title` (`APP_NAME`) identificam o app no painel do OpenRouter.
- `stream_usage=True`, `max_retries=2`, `timeout=90`.

## API

Tudo sob `/v1`, com `Authorization: Bearer <jwt>` ou `X-API-Key` (+ `X-User-Id`).

| Método | Rota                        | O quê                                               |
| ------ | --------------------------- | --------------------------------------------------- |
| POST   | `/threads`                  | Cria thread do usuário                              |
| GET    | `/threads`                  | Lista threads do usuário (`limit` 1–200, padrão 50) |
| GET    | `/threads/{id}`             | Estado: mensagens, `next`, interrupts pendentes     |
| DELETE | `/threads/{id}`             | Apaga thread + checkpoints                          |
| POST   | `/threads/{id}/runs/stream` | Nova mensagem, resposta SSE                         |
| POST   | `/threads/{id}/runs/resume` | Responde um interrupt, resposta SSE                 |
| POST   | `/threads/{id}/runs/wait`   | Nova mensagem, resposta JSON (sem SSE)              |

Fora do `/v1`: `GET /healthz` (processo vivo) e `GET /readyz` (consegue falar com o Postgres).

Regras:

- **Posse**: toda rota com `{id}` passa por `owned_thread`, que só acha a thread se o `user_id` bater. Thread de outro usuário dá 404, não 403.
- **Um run por thread**: lock no Postgres. Um segundo run simultâneo recebe `error: thread_busy` (SSE) ou 409 (`/wait`).
- **Interrupt pendente**: mandar mensagem nova com interrupt pendente dá 409 `pending_interrupt`; chamar `/resume` sem interrupt dá 409 `no_pending_interrupt`.
- **`interrupt_id`** no `/resume` só é necessário quando há mais de um interrupt pendente (o valor vira `{interrupt_id: value}`).
- **Limites**: `RUN_TIMEOUT_SECONDS` (300) por run e `RECURSION_LIMIT` (25) passos do grafo.
- **Título**: ao fim de um run, `touch_thread` atualiza `updated_at` e, se a thread ainda não tem título, usa os primeiros 80 caracteres da mensagem.

## Streaming (SSE)

`api/streaming.py` traduz o `graph.astream(stream_mode=["messages", "updates"])` em eventos tipados:

| Evento        | Quando                                                                      | Payload principal                              |
| ------------- | --------------------------------------------------------------------------- | ---------------------------------------------- |
| `run_started` | Início do run                                                               | `run_id`, `thread_id`                          |
| `token`       | Pedaço de texto de um nó em `STREAMING_NODES`                               | `message_id`, `content`                        |
| `message`     | Mensagem completa ao fim de um nó (inclui tool calls e resultados de tools) | `node`, `message`                              |
| `interrupt`   | O grafo pausou pedindo resposta                                             | `interrupt_id`, `value`                        |
| `done`        | Fim do run                                                                  | `interrupted`, `next`                          |
| `error`       | Falha                                                                       | `code`: `thread_busy`, `timeout` ou `internal` |

Como funciona:

- O grafo roda numa **task produtora** que escreve numa fila; o gerador da resposta só consome a fila. Assim o timeout e o cancelamento afetam só o grafo, nunca o código que escreve no socket.
- **Cliente desconectou** (ex.: botão "Parar" do front): o run é cancelado. Os passos já concluídos ficam no checkpoint. Para runs que precisem sobreviver à desconexão, a produtora teria de ir para um worker.
- A mensagem `message` de um nó tem o mesmo `id` dos tokens que a precederam; o front substitui o texto acumulado pela versão final.
- `ping` a cada 15 s e header `X-Accel-Buffering: no` para proxies não segurarem o stream.

## Observabilidade

`observability.py` liga o Langfuse quando `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY` estão definidas **e** o extra está instalado (`uv sync --extra langfuse`, ou `--build-arg UV_EXTRAS="--extra langfuse"` na imagem). Cada run manda `langfuse_session_id` (thread) e `langfuse_user_id`. Sem o extra, só registra um aviso.

## Startup (`lifespan`)

Ao subir, a API abre o pool, roda as migrations (schema `agent`, tabelas do checkpointer e `agent_threads`), compila o grafo com o `AsyncPostgresSaver` e cria o verificador de JWT. Se o Postgres estiver fora, a API não sobe. Um aviso é registrado se `AUTH_DISABLED=true` fora de `ENV=dev` (a flag é ignorada nesse caso).

## LangGraph Studio

`make studio` roda `langgraph dev` com `langgraph.json`, que aponta para `src/agent/graph/studio.py:graph`. Útil para inspecionar passos, estado e interrupts sem passar pela API. Ele lê `apps/agent/.env` e usa o checkpointer em memória do próprio servidor de dev.
