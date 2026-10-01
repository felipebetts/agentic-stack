'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

import { type ChatMessage, appendToken, toChat, upsert } from './chat-state'
import type { AgentClient } from './client'
import type { InterruptOut, StreamEvent } from './types'

type Status = 'idle' | 'loading' | 'streaming' | 'error'

export function useAgentThread(
  client: AgentClient,
  initialThreadId: string | null = null,
) {
  const [threadId, setThreadId] = useState(initialThreadId)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [interrupt, setInterrupt] = useState<InterruptOut | null>(null)
  const [status, setStatus] = useState<Status>(
    initialThreadId ? 'loading' : 'idle',
  )
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Carrega histórico só para uma thread existente passada de fora.
  useEffect(() => {
    if (!initialThreadId) return
    let cancelled = false
    client
      .getState(initialThreadId)
      .then((s) => {
        if (cancelled) return
        setMessages(s.messages.map((m, i) => toChat(m, `h-${i}`)))
        setInterrupt(s.interrupts[0] ?? null)
        setStatus('idle')
      })
      .catch((e: Error) => {
        if (!cancelled) {
          setError(e.message)
          setStatus('error')
        }
      })
    return () => {
      cancelled = true
    }
  }, [client, initialThreadId])

  const handle = useCallback((ev: StreamEvent) => {
    switch (ev.event) {
      case 'token':
        setMessages((prev) =>
          appendToken(prev, ev.message_id ?? 'streaming', ev.content),
        )
        break
      case 'message':
        setMessages((prev) =>
          upsert(prev, toChat(ev.message, crypto.randomUUID())),
        )
        break
      case 'interrupt':
        setInterrupt({ id: ev.interrupt_id, value: ev.value })
        break
      case 'error':
        setError(ev.message)
        break
      case 'run_started':
      case 'done':
        break
    }
  }, [])

  const run = useCallback(
    async (
      start: (
        threadId: string,
        signal: AbortSignal,
      ) => AsyncGenerator<StreamEvent>,
      ensureThread: boolean,
    ) => {
      const controller = new AbortController()
      abortRef.current = controller
      setError(null)
      setStatus('streaming')
      let failed = false
      try {
        let id = threadId
        if (!id && ensureThread) {
          id = (await client.createThread()).id
          setThreadId(id)
        }
        if (!id) throw new Error('Conversa não encontrada.')
        for await (const ev of start(id, controller.signal)) {
          handle(ev)
          if (ev.event === 'error') failed = true
        }
      } catch (e) {
        if (!controller.signal.aborted) {
          setError((e as Error).message)
          failed = true
        }
      } finally {
        abortRef.current = null
        setStatus(failed ? 'error' : 'idle')
      }
    },
    [client, handle, threadId],
  )

  const send = useCallback(
    (text: string) => {
      setMessages((prev) => [
        ...prev,
        {
          key: `local-${crypto.randomUUID()}`,
          type: 'human',
          content: text,
          tool_calls: [],
          name: null,
        },
      ])
      return run((id, signal) => client.streamRun(id, text, signal), true)
    },
    [client, run],
  )

  const resume = useCallback(
    (value: unknown) => {
      const pending = interrupt
      setInterrupt(null)
      return run(
        (id, signal) => client.resume(id, value, pending?.id, signal),
        false,
      )
    },
    [client, interrupt, run],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  return { threadId, messages, interrupt, status, error, send, resume, stop }
}
