from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    log_level: str = "INFO"

    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_provider_order: list[str] = Field(default_factory=list)
    openrouter_allow_fallbacks: bool = True
    app_url: str = "http://localhost:3000"
    app_name: str = "agent"

    database_url: str
    db_schema: str = "agent"
    db_pool_min: int = 1
    db_pool_max: int = 20

    # URL pública do app web (Better Auth) = BETTER_AUTH_URL. Vira os claims iss/aud esperados.
    auth_url: str = "http://localhost:3000"
    # De onde buscar as chaves públicas. Padrão: {auth_url}/api/auth/jwks. Sobrescreva quando
    # o agent alcança o web por outro endereço (ex.: de dentro de um container).
    auth_jwks_url: str | None = None
    service_api_keys: list[str] = Field(default_factory=list)
    auth_disabled: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    run_timeout_seconds: int = 300
    recursion_limit: int = 25

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
