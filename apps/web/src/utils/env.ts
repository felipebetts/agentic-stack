// Envs do servidor, com erro claro se faltar alguma. Não importe em Client Components:
// fora do servidor elas não existem e `requireEnv` lança.
// Envs do navegador (NEXT_PUBLIC_*) ficam em `public-env.ts`.

const requireEnv = (name: string, optional: boolean = false): string => {
  const value = process.env[name]
  if (!value && !optional) {
    throw new Error(`Missing environment variable: ${name}`)
  }
  return value as string
}

export const DATABASE_URL = requireEnv('DATABASE_URL')
export const BETTER_AUTH_SECRET = requireEnv('BETTER_AUTH_SECRET')
export const BETTER_AUTH_URL = requireEnv('BETTER_AUTH_URL')
