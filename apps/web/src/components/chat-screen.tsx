'use client'

import { useRouter } from 'next/navigation'

import { AgentChat } from '@/components/agent-chat'
import { Button } from '@/components/ui/button'
import { agentClient, clearAgentToken } from '@/lib/agent/instance'
import { authClient } from '@/lib/auth-client'

type Props = { user: { id: string; email: string } }

export function ChatScreen({ user }: Props) {
  const router = useRouter()

  async function signOut() {
    clearAgentToken()
    await authClient.signOut()
    router.refresh()
  }

  return (
    <div className="flex h-dvh flex-col">
      <header className="border-border flex items-center justify-between gap-4 border-b px-4 py-2">
        <span className="font-heading font-medium">Agente</span>
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-muted-foreground truncate text-sm">
            {user.email}
          </span>
          <Button variant="ghost" size="sm" onClick={signOut}>
            Sair
          </Button>
        </div>
      </header>
      {/* key: troca de usuário começa uma conversa nova */}
      <AgentChat key={user.id} client={agentClient} />
    </div>
  )
}
