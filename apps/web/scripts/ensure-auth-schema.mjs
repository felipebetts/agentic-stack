// Cria o schema do Better Auth antes do `auth migrate`. Sem ele, o search_path aponta
// para um schema inexistente e a CLI cria as tabelas em `public` sem avisar.
// O nome precisa bater com o search_path de src/lib/auth.ts.
import pg from 'pg'

// Sem DATABASE_URL o `pg` não falha: conecta com os padrões (usuário do sistema, sem
// senha) e o Postgres responde com um erro de SASL que não diz o que está faltando.
if (!process.env.DATABASE_URL) {
  console.error(
    'DATABASE_URL não definida. Crie o .env.local: cp .env.example .env.local',
  )
  process.exit(1)
}

const client = new pg.Client({ connectionString: process.env.DATABASE_URL })
await client.connect()
try {
  await client.query('create schema if not exists auth')
} finally {
  await client.end()
}
