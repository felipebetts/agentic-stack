import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { ApprovalCard } from '@/components/approval-card'

const emailInterrupt = {
  id: 'i1',
  value: {
    type: 'approval',
    action: 'send_email',
    args: { to: 'fulano@exemplo.com', subject: 'Oi', body: 'Tudo bem?' },
  },
}

test('shows the email draft and sends the decision', () => {
  const onDecide = vi.fn()
  render(
    <ApprovalCard
      interrupt={emailInterrupt}
      disabled={false}
      onDecide={onDecide}
    />,
  )

  expect(screen.getByText('fulano@exemplo.com')).toBeInTheDocument()
  expect(screen.getByText('Tudo bem?')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
  expect(onDecide).toHaveBeenCalledWith({ approved: true })

  fireEvent.click(screen.getByRole('button', { name: 'Recusar' }))
  expect(onDecide).toHaveBeenLastCalledWith({
    approved: false,
    reason: 'rejeitado pelo usuário',
  })
})

test('falls back to an argument list for unknown actions', () => {
  render(
    <ApprovalCard
      interrupt={{
        id: null,
        value: {
          type: 'approval',
          action: 'delete_file',
          args: { path: '/tmp/x' },
        },
      }}
      disabled={false}
      onDecide={() => {}}
    />,
  )
  expect(
    screen.getByText('O agente quer executar delete_file'),
  ).toBeInTheDocument()
  expect(screen.getByText('/tmp/x')).toBeInTheDocument()
})
