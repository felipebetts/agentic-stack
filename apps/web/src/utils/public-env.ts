// Envs embutidas no bundle do navegador. O Next só substitui acessos literais
// (`process.env.NEXT_PUBLIC_X`), então elas não podem passar por `requireEnv`,
// que lê `process.env[name]`.

export const AGENT_URL =
  process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8000'
