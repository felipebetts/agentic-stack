'use client'

import { authClient } from '@/lib/auth-client'
import { AGENT_URL } from '@/utils/public-env'

import { AgentClient } from './client'

// O JWT do Better Auth vale 15 min. Reaproveita até faltar 1 min para expirar.
let cached: { token: string; exp: number } | null = null

const decodeExp = (token: string): number => {
  const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
  return (JSON.parse(atob(payload)) as { exp: number }).exp * 1000
}

async function getToken(): Promise<string | null> {
  if (cached && cached.exp - Date.now() > 60_000) return cached.token
  const { data } = await authClient.$fetch<{ token: string }>('/token', {
    method: 'GET',
  })
  if (!data?.token) {
    cached = null
    return null
  }
  cached = { token: data.token, exp: decodeExp(data.token) }
  return data.token
}

export function clearAgentToken() {
  cached = null
}

export const agentClient = new AgentClient(AGENT_URL, getToken)
