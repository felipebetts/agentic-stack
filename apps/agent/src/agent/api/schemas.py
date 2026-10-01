from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------- REST ----------


class _Out(BaseModel):
    # Campos com default saem como obrigatórios no OpenAPI de resposta (eles sempre
    # vêm no JSON). Sem isso o TS gera tudo opcional.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class ToolCallOut(_Out):
    id: str | None
    name: str
    args: dict[str, Any]


class MessageOut(_Out):
    id: str | None
    type: Literal["human", "ai", "tool", "system"]
    content: str
    tool_calls: list[ToolCallOut] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class InterruptOut(_Out):
    id: str | None
    value: Any


class CreateThreadIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ThreadOut(_Out):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ThreadStateOut(_Out):
    thread_id: UUID
    messages: list[MessageOut]
    next: list[str]
    interrupts: list[InterruptOut]


class RunIn(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)


class ResumeIn(BaseModel):
    value: Any
    interrupt_id: str | None = Field(
        default=None, description="Necessário só quando há mais de um interrupt pendente."
    )


class ErrorOut(_Out):
    code: str
    message: str


# ---------- SSE ----------
# Herdando de _Out, `event` sai obrigatório e o TS gera uma discriminated union.


class _Event(_Out):
    pass


class RunStartedEvent(_Event):
    event: Literal["run_started"] = "run_started"
    run_id: str
    thread_id: str


class TokenEvent(_Event):
    event: Literal["token"] = "token"
    message_id: str | None
    content: str


class MessageEvent(_Event):
    event: Literal["message"] = "message"
    node: str
    message: MessageOut


class InterruptEvent(_Event):
    event: Literal["interrupt"] = "interrupt"
    interrupt_id: str | None
    value: Any


class DoneEvent(_Event):
    event: Literal["done"] = "done"
    run_id: str
    interrupted: bool
    next: list[str]


class ErrorEvent(_Event):
    event: Literal["error"] = "error"
    code: Literal["thread_busy", "timeout", "internal"]
    message: str


StreamEvent = Annotated[
    RunStartedEvent | TokenEvent | MessageEvent | InterruptEvent | DoneEvent | ErrorEvent,
    Field(discriminator="event"),
]
