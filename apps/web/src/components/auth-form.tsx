'use client'

import { useRouter } from 'next/navigation'
import { type FormEvent, useState } from 'react'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { authClient } from '@/lib/auth-client'

type Mode = 'signin' | 'signup'

const COPY: Record<
  Mode,
  { title: string; description: string; submit: string; toggle: string }
> = {
  signin: {
    title: 'Entrar',
    description: 'Use seu email e senha para continuar suas conversas.',
    submit: 'Entrar',
    toggle: 'Criar uma conta',
  },
  signup: {
    title: 'Criar conta',
    description: 'Suas conversas com o agente ficam salvas nesta conta.',
    submit: 'Criar conta',
    toggle: 'Já tenho conta',
  },
}

export function AuthForm() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>('signin')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const copy = COPY[mode]

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const email = String(form.get('email'))
    const password = String(form.get('password'))
    setError(null)
    setPending(true)
    const { error } =
      mode === 'signin'
        ? await authClient.signIn.email({ email, password })
        : await authClient.signUp.email({
            name: String(form.get('name')),
            email,
            password,
          })
    if (error) {
      setPending(false)
      setError(error.message ?? 'Não foi possível entrar. Tente de novo.')
      return
    }
    router.refresh()
  }

  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">{copy.title}</CardTitle>
          <CardDescription>{copy.description}</CardDescription>
        </CardHeader>
        <form onSubmit={onSubmit}>
          <CardContent className="flex flex-col gap-4">
            {mode === 'signup' && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="name">Nome</Label>
                <Input id="name" name="name" autoComplete="name" required />
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Senha</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete={
                  mode === 'signin' ? 'current-password' : 'new-password'
                }
                minLength={8}
                required
              />
              {mode === 'signup' && (
                <p className="text-muted-foreground text-xs">
                  Pelo menos 8 caracteres.
                </p>
              )}
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
          <CardFooter className="mt-4 flex flex-col gap-2">
            <Button type="submit" className="w-full" disabled={pending}>
              {pending && <Spinner />}
              {copy.submit}
            </Button>
            <Button
              type="button"
              variant="link"
              onClick={() => {
                setMode(mode === 'signin' ? 'signup' : 'signin')
                setError(null)
              }}
            >
              {copy.toggle}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </main>
  )
}
