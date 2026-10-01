"""Valida JWTs no formato do plugin jwt do Better Auth (EdDSA/Ed25519 + JWKS), sem rede."""

import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt.algorithms import OKPAlgorithm

from agent.api.auth import AuthError, JwtVerifier
from agent.config import Settings

BASE = "http://localhost:3000"


@pytest.fixture
def key():
    return Ed25519PrivateKey.generate()


@pytest.fixture
def verifier(key, monkeypatch):
    v = JwtVerifier(Settings(auth_url=BASE))
    jwk = json.loads(OKPAlgorithm.to_jwk(key.public_key())) | {"kid": "k1", "alg": "EdDSA"}
    monkeypatch.setattr(v._jwks, "fetch_data", lambda: {"keys": [jwk]})
    return v


def sign(key, **overrides):
    now = int(time.time())
    claims = {"sub": "user-1", "iss": BASE, "aud": BASE, "iat": now, "exp": now + 900}
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="EdDSA", headers={"kid": "k1"})


async def test_accepts_valid_token(key, verifier):
    claims = await verifier.verify(sign(key))
    assert claims["sub"] == "user-1"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "http://outro-app"},
        {"iss": "http://outro-app"},
        {"exp": int(time.time()) - 10},
    ],
)
async def test_rejects_wrong_claims(key, verifier, overrides):
    with pytest.raises(AuthError):
        await verifier.verify(sign(key, **overrides))


async def test_rejects_other_key(verifier):
    with pytest.raises(AuthError):
        await verifier.verify(sign(Ed25519PrivateKey.generate()))


async def test_rejects_hs256(verifier):
    token = jwt.encode({"sub": "x"}, "segredo-qualquer-com-32-bytes-ok!", algorithm="HS256")
    with pytest.raises(AuthError, match="alg não permitido"):
        await verifier.verify(token)
