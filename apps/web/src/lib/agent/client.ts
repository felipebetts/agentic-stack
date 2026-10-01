import { parseSSE } from './sse'
import type { ApiError, StreamEvent, ThreadOut, ThreadStateOut } from './types'

export type TokenProvider = () => Promise<string | null>

export class AgentApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message)
  }
}

export class AgentClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getToken: TokenProvider = async () => null,
  ) {}

  createThread(title?: string): Promise<ThreadOut> {
    return this.json('POST', '/threads', { title: title ?? null })
  }

  listThreads(limit = 50): Promise<ThreadOut[]> {
    return this.json('GET', `/threads?limit=${limit}`)
  }

  getState(threadId: string): Promise<ThreadStateOut> {
    return this.json('GET', `/threads/${threadId}`)
  }

  async deleteThread(threadId: string): Promise<void> {
    await this.request('DELETE', `/threads/${threadId}`)
  }

  streamRun(threadId: string, message: string, signal?: AbortSignal) {
    return this.stream(`/threads/${threadId}/runs/stream`, { message }, signal)
  }

  resume(
    threadId: string,
    value: unknown,
    interruptId?: string | null,
    signal?: AbortSignal,
  ) {
    return this.stream(
      `/threads/${threadId}/runs/resume`,
      { value, interrupt_id: interruptId ?? null },
      signal,
    )
  }

  private async *stream(path: string, body: unknown, signal?: AbortSignal) {
    const res = await this.request(
      'POST',
      path,
      body,
      signal,
      'text/event-stream',
    )
    if (!res.body)
      throw new AgentApiError(res.status, 'no_body', 'resposta sem corpo')
    for await (const raw of parseSSE(res.body)) {
      yield JSON.parse(raw.data) as StreamEvent
    }
  }

  private async json<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const res = await this.request(method, path, body)
    return (await res.json()) as T
  }

  private async request(
    method: string,
    path: string,
    body?: unknown,
    signal?: AbortSignal,
    accept = 'application/json',
  ): Promise<Response> {
    const token = await this.getToken()
    const res = await fetch(`${this.baseUrl}/v1${path}`, {
      method,
      signal,
      headers: {
        accept,
        ...(body !== undefined && { 'content-type': 'application/json' }),
        ...(token && { authorization: `Bearer ${token}` }),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    if (!res.ok) {
      const detail = (await res.json().catch(() => null))?.detail as
        ApiError | undefined
      throw new AgentApiError(
        res.status,
        detail?.code ?? 'http_error',
        detail?.message ?? res.statusText,
      )
    }
    return res
  }
}
