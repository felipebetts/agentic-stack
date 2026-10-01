'use client'

import { RiShieldCheckLine } from '@remixicon/react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { type ApprovalRequest, isApproval } from '@/lib/agent/chat-state'
import type { InterruptOut } from '@/lib/agent/types'

// Como cada ação aparece para quem aprova. Ações sem entrada aqui caem no
// formato genérico (lista de argumentos).
const ACTIONS: Record<string, { title: string; approve: string }> = {
  send_email: { title: 'O agente quer enviar este email', approve: 'Enviar' },
}

type Props = {
  interrupt: InterruptOut
  disabled: boolean
  onDecide: (value: unknown) => void
}

export function ApprovalCard({ interrupt, disabled, onDecide }: Props) {
  const request = isApproval(interrupt.value) ? interrupt.value : null
  const action = request ? ACTIONS[request.action] : undefined

  return (
    <Card className="border-primary/40 ring-primary/30" role="group">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RiShieldCheckLine className="size-4" aria-hidden />
          {action?.title ??
            (request
              ? `O agente quer executar ${request.action}`
              : 'O agente precisa de uma resposta')}
        </CardTitle>
        <CardDescription>Nada acontece até você decidir.</CardDescription>
      </CardHeader>
      <CardContent>
        {request?.action === 'send_email' ? (
          <EmailDraft args={request.args} />
        ) : request ? (
          <ArgsList args={request.args} />
        ) : (
          <pre className="text-xs whitespace-pre-wrap">
            {JSON.stringify(interrupt.value, null, 2)}
          </pre>
        )}
      </CardContent>
      <CardFooter className="gap-2">
        <Button
          disabled={disabled}
          onClick={() => onDecide({ approved: true })}
        >
          {action?.approve ?? 'Aprovar'}
        </Button>
        <Button
          variant="outline"
          disabled={disabled}
          onClick={() =>
            onDecide({ approved: false, reason: 'rejeitado pelo usuário' })
          }
        >
          Recusar
        </Button>
      </CardFooter>
    </Card>
  )
}

function EmailDraft({ args }: { args: ApprovalRequest['args'] }) {
  return (
    <div className="bg-muted flex flex-col gap-3 rounded-lg p-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Para</dt>
        <dd className="min-w-0 wrap-break-word">{String(args.to ?? '')}</dd>
        <dt className="text-muted-foreground">Assunto</dt>
        <dd className="min-w-0 font-medium wrap-break-word">
          {String(args.subject ?? '')}
        </dd>
      </dl>
      <p className="border-border border-t pt-3 text-sm leading-relaxed whitespace-pre-wrap">
        {String(args.body ?? '')}
      </p>
    </div>
  )
}

function ArgsList({ args }: { args: ApprovalRequest['args'] }) {
  return (
    <dl className="bg-muted grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-lg p-3 text-sm">
      {Object.entries(args).map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="text-muted-foreground">{key}</dt>
          <dd className="min-w-0 wrap-break-word whitespace-pre-wrap">
            {typeof value === 'string' ? value : JSON.stringify(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}
