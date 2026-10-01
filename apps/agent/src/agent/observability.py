import logging
from typing import Any

from agent.config import get_settings

log = logging.getLogger(__name__)


def get_callbacks() -> list[Any]:
    """Callbacks de tracing. Langfuse lê LANGFUSE_* do ambiente do processo."""
    s = get_settings()
    if not (s.langfuse_public_key and s.langfuse_secret_key):
        return []
    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        log.warning("LANGFUSE_* definido mas o extra 'langfuse' não está instalado")
        return []
    return [CallbackHandler()]
