import { type RemixiconComponentType, RiLoaderLine } from '@remixicon/react'
import { cn } from 'cn'

// Tipado pelos props do ícone: o gerado (`ComponentProps<'svg'>`) inclui `children`,
// que os ícones do Remix não aceitam, e quebrava o typecheck.
function Spinner({
  className,
  ...props
}: React.ComponentProps<RemixiconComponentType>) {
  return (
    <RiLoaderLine
      data-slot="spinner"
      role="status"
      aria-label="Carregando"
      className={cn('size-4 animate-spin', className)}
      {...props}
    />
  )
}

export { Spinner }
