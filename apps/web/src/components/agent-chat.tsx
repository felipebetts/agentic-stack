'use client'

import { type FormEvent, type KeyboardEvent, useState } from 'react'

import {
  RiArrowUpLine,
  RiCheckLine,
  RiStopFill,
  RiToolsLine,
} from '@remixicon/react'

import { ApprovalCard } from '@/components/approval-card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Bubble, BubbleContent } from '@/components/ui/bubble'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from '@/components/ui/input-group'
import { Marker, MarkerContent, MarkerIcon } from '@/components/ui/marker'
import { Message, MessageContent } from '@/components/ui/message'
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from '@/components/ui/message-scroller'
import { Spinner } from '@/components/ui/spinner'
import type { ChatMessage } from '@/lib/agent/chat-state'
import type { AgentClient } from '@/lib/agent/client'
import { useAgentThread } from '@/lib/agent/use-agent-thread'

// Nome das tools como o usuário entende. Tools sem entrada aparecem pelo nome técnico.
const TOOL_LABELS: Record<string, string> = {
  get_weather: 'previsão do tempo',
  send_email: 'envio de email',
}
const toolLabel = (name: string | null) =>
  (name && TOOL_LABELS[name]) ?? name ?? 'ferramenta'

const SUGGESTIONS = [
  'Como está o tempo em Belo Horizonte?',
  'Manda um email para fulano@exemplo.com dizendo oi',
]

type Props = { client: AgentClient; threadId?: string }

export function AgentChat({ client, threadId }: Props) {
  const { messages, interrupt, status, error, send, resume, stop } =
    useAgentThread(client, threadId ?? null)
  const [input, setInput] = useState('')
  const busy = status === 'streaming' || status === 'loading'
  const last = messages.at(-1)
  const thinking =
    status === 'streaming' && (!last || last.type !== 'ai' || !last.content)

  function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed || busy || interrupt) return
    setInput('')
    void send(trimmed)
  }

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    submit(input)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      submit(input)
    }
  }

  return (
    <MessageScrollerProvider autoScroll>
      <MessageScroller className="flex-1">
        <MessageScrollerViewport>
          <MessageScrollerContent className="mx-auto w-full max-w-2xl px-4 py-6">
            {messages.length === 0 && !busy && <EmptyState onPick={submit} />}
            {messages.map((m) => (
              <MessageScrollerItem
                key={m.key}
                messageId={m.key}
                scrollAnchor={m.type === 'human'}
              >
                <ChatItem message={m} />
              </MessageScrollerItem>
            ))}
            {thinking && (
              <MessageScrollerItem>
                <Marker role="status">
                  <MarkerIcon>
                    <Spinner />
                  </MarkerIcon>
                  <MarkerContent>Pensando…</MarkerContent>
                </Marker>
              </MessageScrollerItem>
            )}
            {interrupt && (
              <MessageScrollerItem scrollAnchor>
                <ApprovalCard
                  interrupt={interrupt}
                  disabled={busy}
                  onDecide={resume}
                />
              </MessageScrollerItem>
            )}
            {error && (
              <MessageScrollerItem>
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              </MessageScrollerItem>
            )}
          </MessageScrollerContent>
        </MessageScrollerViewport>
        <MessageScrollerButton />
      </MessageScroller>

      <form
        onSubmit={onSubmit}
        className="mx-auto w-full max-w-2xl px-4 pb-4"
        aria-label="Enviar mensagem"
      >
        <InputGroup>
          <InputGroupTextarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              interrupt
                ? 'Responda o pedido de aprovação acima'
                : 'Peça algo ao agente'
            }
            disabled={!!interrupt}
            aria-label="Mensagem"
            className="max-h-48 min-h-12"
          />
          <InputGroupAddon align="block-end">
            <span className="text-muted-foreground text-xs">
              Enter envia, Shift+Enter quebra a linha
            </span>
            {status === 'streaming' ? (
              <InputGroupButton
                size="icon-sm"
                variant="secondary"
                className="ml-auto"
                onClick={stop}
              >
                <RiStopFill />
                <span className="sr-only">Parar resposta</span>
              </InputGroupButton>
            ) : (
              <InputGroupButton
                type="submit"
                size="icon-sm"
                variant="default"
                className="ml-auto"
                disabled={busy || !!interrupt || !input.trim()}
              >
                <RiArrowUpLine />
                <span className="sr-only">Enviar</span>
              </InputGroupButton>
            )}
          </InputGroupAddon>
        </InputGroup>
      </form>
    </MessageScrollerProvider>
  )
}

function ChatItem({ message: m }: { message: ChatMessage }) {
  if (m.type === 'human') {
    return (
      <Message align="end">
        <MessageContent>
          <Bubble>
            <BubbleContent className="whitespace-pre-wrap">
              {m.content}
            </BubbleContent>
          </Bubble>
        </MessageContent>
      </Message>
    )
  }

  if (m.type === 'tool') {
    return (
      <Marker>
        <MarkerIcon>
          <RiCheckLine />
        </MarkerIcon>
        <MarkerContent>
          {m.content || `${toolLabel(m.name)} concluído`}
        </MarkerContent>
      </Marker>
    )
  }

  return (
    <Message>
      <MessageContent>
        {m.content && (
          <Bubble variant="ghost">
            <BubbleContent className="whitespace-pre-wrap">
              {m.content}
            </BubbleContent>
          </Bubble>
        )}
        {m.tool_calls.map((tc) => (
          <Marker key={tc.id ?? tc.name}>
            <MarkerIcon>
              <RiToolsLine />
            </MarkerIcon>
            <MarkerContent>Usando {toolLabel(tc.name)}</MarkerContent>
          </Marker>
        ))}
      </MessageContent>
    </Message>
  )
}

function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="flex flex-1 flex-col justify-end gap-6 pb-4">
      <div className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-medium">
          O que o agente deve fazer?
        </h1>
        <p className="text-muted-foreground max-w-prose text-sm">
          Ele usa ferramentas para executar o pedido. Antes de qualquer ação com
          efeito fora daqui, como enviar um email, ele pede sua aprovação.
        </p>
      </div>
      <Message align="end">
        <MessageContent>
          {SUGGESTIONS.map((s) => (
            <Bubble key={s} variant="outline">
              <BubbleContent
                render={<button type="button" />}
                onClick={() => onPick(s)}
              >
                {s}
              </BubbleContent>
            </Bubble>
          ))}
        </MessageContent>
      </Message>
    </div>
  )
}
