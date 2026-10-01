import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

import { cn } from '@/lib/utils'

import './globals.css'

// Fallback fora do ecossistema Apple: em macOS/iOS a pilha de fontes em
// globals.css resolve para a SF Pro do sistema antes de chegar aqui.
const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'Agente',
  description: 'Converse com o agente e aprove as ações dele.',
}

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="pt-BR" className={cn('h-full', 'antialiased', inter.variable)}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  )
}
