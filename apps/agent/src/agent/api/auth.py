import asyncio
import hmac
import logging
from dataclasses import dataclass
from typing import Literal

import jwt
from jwt import PyJWKClient

from agent.config import Settings

log = logging.getLogger(__name__)

# Só assimétricos (os que o plugin jwt do Better Auth emite). Sem HS256: a chave
# vem do JWKS público, e aceitar HMAC abriria alg confusion.
_ALLOWED_ALGS = {"EdDSA", "ES256", "ES512", "PS256", "RS256"}


@dataclass(frozen=True)
class Principal:
    user_id: str
    kind: Literal["user", "service", "dev"]


class AuthError(Exception):
    pass


class JwtVerifier:
    """Valida o JWT emitido pelo plugin jwt do Better Auth (app web).

    A chave pública vem do JWKS do app web (cacheado, rebuscado quando aparece um
    `kid` novo). Por padrão o Better Auth usa a URL base do app como `iss` e `aud`.
    """

    def __init__(self, s: Settings):
        base = s.auth_url.rstrip("/")
        self._iss = self._aud = base
        self._jwks = PyJWKClient(s.auth_jwks_url or f"{base}/api/auth/jwks", lifespan=600)

    async def verify(self, token: str) -> dict:
        try:
            alg = jwt.get_unverified_header(token).get("alg")
            if alg not in _ALLOWED_ALGS:
                raise AuthError(f"alg não permitido: {alg}")
            key = (await asyncio.to_thread(self._jwks.get_signing_key_from_jwt, token)).key
            return jwt.decode(
                token,
                key,
                algorithms=[alg],
                audience=self._aud,
                issuer=self._iss,
                options={"require": ["exp", "sub"]},
            )
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e


async def authenticate(
    s: Settings,
    verifier: JwtVerifier,
    *,
    authorization: str | None,
    api_key: str | None,
    on_behalf_of: str | None,
) -> Principal:
    # Chamadas servidor-a-servidor (cron, outro backend, n8n). O chamador
    # informa em nome de qual usuário age via X-User-Id.
    if api_key:
        if any(hmac.compare_digest(api_key, k) for k in s.service_api_keys):
            return Principal(user_id=on_behalf_of or "service", kind="service")
        raise AuthError("API key inválida")

    if authorization and authorization.lower().startswith("bearer "):
        claims = await verifier.verify(authorization[7:])
        return Principal(user_id=claims["sub"], kind="user")

    if s.auth_disabled and s.is_dev:
        return Principal(user_id="dev-user", kind="dev")

    raise AuthError("credenciais ausentes")
