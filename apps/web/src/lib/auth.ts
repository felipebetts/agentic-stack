import { betterAuth } from 'better-auth'
import { nextCookies } from 'better-auth/next-js'
import { jwt } from 'better-auth/plugins/jwt'
import { Pool } from 'pg'

// Import relativo (não `@/`): a CLI do Better Auth (`pnpm auth:migrate`) carrega este
// arquivo fora do Next.
import { BETTER_AUTH_SECRET, BETTER_AUTH_URL, DATABASE_URL } from '../utils/env'

// Usuários e sessões no mesmo Postgres do agent, num schema próprio (`auth`; o agent usa
// `agent`). O search_path é fixado: o padrão "$user", public mandaria as tabelas para o
// schema com o nome do usuário do banco.
// O plugin jwt emite tokens curtos para a API do agent e publica as chaves públicas em
// /api/auth/jwks, que o agent usa para validar.
// Tabelas: `pnpm auth:migrate` (cria o schema e roda a CLI do Better Auth).
export const auth = betterAuth({
  secret: BETTER_AUTH_SECRET,
  baseURL: BETTER_AUTH_URL,
  database: new Pool({
    connectionString: DATABASE_URL,
    options: '-c search_path=auth',
  }),
  emailAndPassword: { enabled: true },
  plugins: [jwt(), nextCookies()],
})
