from typing import Any

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
async def get_weather(city: str) -> str:
    """Retorna a previsão do tempo atual para uma cidade."""
    return f"Ensolarado, 28°C em {city}."


@tool
async def send_email(to: str, subject: str, body: str) -> str:
    """Envia um email. Exige aprovação humana antes de executar."""
    # Pausa o grafo. No resume, a tool roda de novo do início e `interrupt`
    # devolve o valor enviado em Command(resume=...). Por isso, nada com efeito
    # colateral deve vir ANTES do interrupt.
    decision: Any = interrupt(
        {
            "type": "approval",
            "action": "send_email",
            "args": {"to": to, "subject": subject, "body": body},
        }
    )
    if not isinstance(decision, dict) or not decision.get("approved"):
        reason = decision.get("reason") if isinstance(decision, dict) else None
        return f"Envio cancelado pelo usuário. Motivo: {reason or 'não informado'}."

    # TODO: integração real (Resend, SES...)
    return f"Email enviado para {to}."


TOOLS = [get_weather, send_email]
