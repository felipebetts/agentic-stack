import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import TypeAdapter

from agent.api.auth import JwtVerifier
from agent.api.routes import runs, threads
from agent.api.schemas import StreamEvent
from agent.config import get_settings
from agent.graph.builder import build_graph
from agent.persistence.migrations import run_migrations
from agent.persistence.pool import create_pool

log = logging.getLogger("agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    if s.auth_disabled and not s.is_dev:
        log.warning("AUTH_DISABLED ignorado fora de ENV=dev")

    pool = create_pool(s)
    await pool.open(wait=True)
    checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
    await run_migrations(pool, checkpointer, s.db_schema)

    app.state.pool = pool
    app.state.graph = build_graph(checkpointer)
    app.state.verifier = JwtVerifier(s)
    try:
        yield
    finally:
        await pool.close()


def _install_openapi(app: FastAPI) -> None:
    """Injeta a union de eventos SSE no OpenAPI, para o front gerar tipos."""

    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        events = TypeAdapter(StreamEvent).json_schema(
            mode="serialization", ref_template="#/components/schemas/{model}"
        )
        components = schema.setdefault("components", {}).setdefault("schemas", {})
        components.update(events.pop("$defs", {}))
        components["StreamEvent"] = events
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


def create_app() -> FastAPI:
    s = get_settings()
    logging.basicConfig(level=s.log_level)

    app = FastAPI(title="Agent API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["authorization", "content-type", "x-api-key", "x-user-id"],
    )

    v1 = APIRouter(prefix="/v1")
    v1.include_router(threads.router)
    v1.include_router(runs.router)
    app.include_router(v1)

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return {"ok": True}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request):
        async with request.app.state.pool.connection() as conn:
            await conn.execute("select 1")
        return {"ok": True}

    _install_openapi(app)
    return app


app = create_app()
