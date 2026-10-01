// Tipos derivados do contrato gerado (schema.d.ts). Não edite schema.d.ts à mão:
// rode `make contract` na raiz.
import type { components } from './schema'

type Schemas = components['schemas']

export type StreamEvent = Schemas['StreamEvent']
export type MessageOut = Schemas['MessageOut']
export type InterruptOut = Schemas['InterruptOut']
export type ThreadOut = Schemas['ThreadOut']
export type ThreadStateOut = Schemas['ThreadStateOut']
export type ApiError = Schemas['ErrorOut']
