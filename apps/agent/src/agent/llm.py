from typing import Any

from langchain_openai import ChatOpenAI

from agent.config import get_settings


def get_llm(model: str | None = None, **kwargs: Any) -> ChatOpenAI:
    """ChatOpenAI apontando para o OpenRouter.

    `require_parameters` faz o OpenRouter rotear só para providers que suportam
    todos os parâmetros enviados (tools, response_format). Sem isso, o mesmo
    modelo pode cair num provider que ignora tool calling.
    """
    s = get_settings()
    provider: dict[str, Any] = {"require_parameters": True}
    if s.openrouter_provider_order:
        provider["order"] = s.openrouter_provider_order
        provider["allow_fallbacks"] = s.openrouter_allow_fallbacks

    return ChatOpenAI(
        model=model or s.openrouter_model,
        base_url=s.openrouter_base_url,
        api_key=s.openrouter_api_key,
        default_headers={"HTTP-Referer": s.app_url, "X-Title": s.app_name},
        extra_body={"provider": provider},
        stream_usage=True,
        max_retries=2,
        timeout=90,
        **kwargs,
    )
