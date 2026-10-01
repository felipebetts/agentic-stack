export type RawSSE = { event: string; data: string }

/** Parser SSE mínimo para fetch() (EventSource não suporta POST nem headers). */
export async function* parseSSE(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<RawSSE> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) return
      buffer += decoder.decode(value, { stream: true })

      let match: RegExpExecArray | null
      while ((match = /\r?\n\r?\n/.exec(buffer))) {
        const block = buffer.slice(0, match.index)
        buffer = buffer.slice(match.index + match[0].length)

        let event = 'message'
        const data: string[] = []
        for (const line of block.split(/\r?\n/)) {
          if (!line || line.startsWith(':')) continue // comentários = ping
          const i = line.indexOf(':')
          const field = i === -1 ? line : line.slice(0, i)
          const value = i === -1 ? '' : line.slice(i + 1).replace(/^ /, '')
          if (field === 'event') event = value
          else if (field === 'data') data.push(value)
        }
        if (data.length) yield { event, data: data.join('\n') }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
