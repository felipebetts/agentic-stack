import { expect, test } from 'vitest'

import { parseSSE } from '@/lib/agent/sse'

function streamOf(...chunks: string[]) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(encoder.encode(c))
      controller.close()
    },
  })
}

async function collect(stream: ReadableStream<Uint8Array>) {
  const out = []
  for await (const ev of parseSSE(stream)) out.push(ev)
  return out
}

test('parses events split across chunks', async () => {
  const events = await collect(
    streamOf(
      'event: token\ndata: {"a":',
      '1}\n\nevent: done\r\ndata: {}\r\n\r\n',
    ),
  )
  expect(events).toEqual([
    { event: 'token', data: '{"a":1}' },
    { event: 'done', data: '{}' },
  ])
})

test('ignores ping comments and joins multi-line data', async () => {
  const events = await collect(
    streamOf(': ping\n\ndata: linha 1\ndata: linha 2\n\n'),
  )
  expect(events).toEqual([{ event: 'message', data: 'linha 1\nlinha 2' }])
})
