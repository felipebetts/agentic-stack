import { headers } from 'next/headers'

import { AuthForm } from '@/components/auth-form'
import { ChatScreen } from '@/components/chat-screen'
import { auth } from '@/lib/auth'

export default async function Home() {
  const session = await auth.api.getSession({ headers: await headers() })

  if (!session) return <AuthForm />

  return (
    <ChatScreen user={{ id: session.user.id, email: session.user.email }} />
  )
}
