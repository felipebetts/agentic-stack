import { expect, test } from 'vitest'

import {
  type ChatMessage,
  appendToken,
  isApproval,
  upsert,
} from '@/lib/agent/chat-state'

const ai = (key: string, content: string): ChatMessage => ({
  key,
  type: 'ai',
  content,
  tool_calls: [],
  name: null,
})

test('tokens accumulate into one streaming message', () => {
  let list = appendToken([], 'm1', 'Olá')
  list = appendToken(list, 'm1', ', tudo bem?')
  expect(list).toEqual([ai('m1', 'Olá, tudo bem?')])
})

test('final message replaces the streamed one with the same key', () => {
  const list = upsert([ai('m1', 'parcial')], ai('m1', 'completa'))
  expect(list).toEqual([ai('m1', 'completa')])
})

test('isApproval recognizes approval interrupts only', () => {
  expect(isApproval({ type: 'approval', action: 'send_email', args: {} })).toBe(
    true,
  )
  expect(isApproval({ type: 'other' })).toBe(false)
  expect(isApproval('texto')).toBe(false)
})
