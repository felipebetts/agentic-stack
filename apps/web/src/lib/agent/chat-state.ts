import type { InterruptOut, MessageOut } from './types'

export type ChatMessage = Pick<
  MessageOut,
  'type' | 'content' | 'tool_calls' | 'name'
> & {
  key: string
}

export type ApprovalRequest = {
  type: 'approval'
  action: string
  args: Record<string, unknown>
}

export const isApproval = (
  value: InterruptOut['value'],
): value is ApprovalRequest =>
  typeof value === 'object' &&
  value !== null &&
  (value as { type?: unknown }).type === 'approval'

export const toChat = (m: MessageOut, fallbackKey: string): ChatMessage => ({
  key: m.id ?? fallbackKey,
  type: m.type,
  content: m.content,
  tool_calls: m.tool_calls,
  name: m.name,
})

/** Mensagem final de um nó substitui a versão parcial (tokens) com o mesmo id. */
export function upsert(list: ChatMessage[], msg: ChatMessage): ChatMessage[] {
  const i = list.findIndex((m) => m.key === msg.key)
  if (i === -1) return [...list, msg]
  const next = list.slice()
  next[i] = msg
  return next
}

export function appendToken(
  list: ChatMessage[],
  key: string,
  token: string,
): ChatMessage[] {
  const i = list.findIndex((m) => m.key === key)
  if (i === -1)
    return [
      ...list,
      { key, type: 'ai', content: token, tool_calls: [], name: null },
    ]
  const next = list.slice()
  next[i] = { ...next[i], content: next[i].content + token }
  return next
}
